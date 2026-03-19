// This file runs as a Web Worker module bundled by Vite.

import {
  AutoProcessor,
  AutoModelForObjectDetection,
  AutoModelForImageClassification,
  RawImage,
  Tensor,
  softmax,
  topk,
  env,
} from "@huggingface/transformers";
import type { ModelConfig, WorkerInMessage, WorkerOutMessage } from "./models";
import type { InferenceResult, InferenceBox } from "@common/types";

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

env.useBrowserCache = true;
env.allowRemoteModels = true;
// In dev, the vite models-404 middleware returns proper 404s for missing local
// model files so transformers.js can fall back to HuggingFace Hub. In prod the
// static server returns an HTML 404 page which transformers.js tries to parse
// as JSON and fails. Disable local model lookup in production.
env.allowLocalModels = import.meta.env.DEV;

// ---------------------------------------------------------------------------
// Types for post-processing output
// ---------------------------------------------------------------------------

interface PostProcessedDetection {
  boxes: number[][];
  classes: number[];
  scores: number[];
}

// ---------------------------------------------------------------------------
// Worker-specific helpers
// ---------------------------------------------------------------------------

/** Send a typed message from the worker to the main thread. */
function send(msg: WorkerOutMessage): void {
  (
    globalThis as unknown as { postMessage(msg: WorkerOutMessage): void }
  ).postMessage(msg);
}

type DeviceType = "webgpu" | "wasm";

/** Detect whether WebGPU is available in this worker context. */
async function getDevice(): Promise<DeviceType> {
  try {
    if (typeof navigator !== "undefined" && "gpu" in (navigator as object)) {
      const adapter = await (
        navigator as unknown as {
          gpu: { requestAdapter(): Promise<unknown | null> };
        }
      ).gpu.requestAdapter();
      if (adapter) {
        console.log("[worker] WebGPU adapter available");
        return "webgpu";
      }
      console.warn(
        "[worker] WebGPU API present but no adapter available, falling back to WASM",
      );
    }
  } catch (err) {
    console.warn(
      "[worker] WebGPU detection failed, falling back to WASM:",
      err,
    );
  }
  return "wasm";
}

/** Crop a rectangular region from an ImageBitmap using OffscreenCanvas. */
async function cropRegion(
  bitmap: ImageBitmap,
  xmin: number,
  ymin: number,
  xmax: number,
  ymax: number,
): Promise<string> {
  const w = Math.max(1, Math.round(xmax - xmin));
  const h = Math.max(1, Math.round(ymax - ymin));
  const canvas = new OffscreenCanvas(w, h);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("OffscreenCanvas 2D context unavailable");
  ctx.drawImage(bitmap, Math.round(xmin), Math.round(ymin), w, h, 0, 0, w, h);
  const blob = await canvas.convertToBlob({ type: "image/jpeg", quality: 0.9 });
  return URL.createObjectURL(blob);
}

// ---------------------------------------------------------------------------
// Processor size patching
// ---------------------------------------------------------------------------

/**
 * Some HuggingFace models (e.g. RT-DETR from cfia-ai-lab) use
 * `{ max_height, max_width }` in their preprocessor_config.json `size` field.
 * transformers.js doesn't support this format, so we convert it to
 * `{ longest_edge }` which preserves aspect ratio.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function patchProcessorSize(processor: any): void {
  // AutoProcessor wraps an image_processor; try both paths
  const imageProcessor = processor?.image_processor ?? processor;
  if (!imageProcessor?.size) {
    console.log("[worker] No image processor size to patch");
    return;
  }

  const size = imageProcessor.size;
  console.log("[worker] Processor size config:", JSON.stringify(size));

  if (size.max_height !== undefined && size.max_width !== undefined) {
    const longest = Math.min(size.max_height, size.max_width);
    console.log(
      `[worker] Patching processor size: {max_height: ${size.max_height}, max_width: ${size.max_width}} → {longest_edge: ${longest}}`,
    );
    imageProcessor.size = { longest_edge: longest };
  }
}

// ---------------------------------------------------------------------------
// Pipeline state
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let detectorModel: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let detectorProcessor: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let classifierModel: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let classifierProcessor: any = null;
let loadedConfig: ModelConfig | null = null;

// ---------------------------------------------------------------------------
// Progress callback factory
// ---------------------------------------------------------------------------

type ProgressInfo = {
  status: string;
  name?: string;
  file?: string;
  progress?: number;
};

function makeProgressCallback(phase: "detector" | "classifier") {
  let lastSent = 0;
  return (info: ProgressInfo): void => {
    if (info.status === "progress" && info.progress !== undefined) {
      const now = Date.now();
      if (now - lastSent < 100 && info.progress < 100) return;
      lastSent = now;
      send({
        type: "model-progress",
        name: `${phase}: ${info.file ?? info.name ?? ""}`,
        progress: info.progress,
      });
    }
  };
}

// ---------------------------------------------------------------------------
// Message handler
// ---------------------------------------------------------------------------

addEventListener("message", async (event: MessageEvent) => {
  const data = event.data as WorkerInMessage;

  // ── Load models ──────────────────────────────────────────────────────────
  if (data.type === "load-models") {
    const config = data.config;
    const device = await getDevice();
    // WebGPU has precision issues with detection models — use WASM for detector
    const detectorDevice: DeviceType = "wasm";
    const classifierDevice = device;
    const progressDetector = makeProgressCallback("detector");
    const progressClassifier = makeProgressCallback("classifier");

    try {
      send({ type: "status", status: "loading-model" });

      console.log(
        "[worker] Loading detector model:",
        config.detectorModel,
        "device:",
        detectorDevice,
      );
      console.log(
        "[worker] Loading classifier model:",
        config.classifierModel,
        "device:",
        classifierDevice,
      );

      // Load detector processor + model (always WASM for precision)
      const [detProc, detMod] = await Promise.all([
        AutoProcessor.from_pretrained(config.detectorModel),
        AutoModelForObjectDetection.from_pretrained(config.detectorModel, {
          device: detectorDevice,
          dtype: "fp32" as const,
          model_file_name: config.detectorModelFileName ?? "model",
          progress_callback: progressDetector as unknown as (
            progress: unknown,
          ) => void,
        }),
      ]);

      console.log("[worker] Detector loaded, patching processor...");
      patchProcessorSize(detProc);
      detectorProcessor = detProc;
      detectorModel = detMod;
      console.log(
        "[worker] Detector id2label:",
        JSON.stringify(detMod.config?.id2label ?? {}),
      );

      // Load classifier processor + model (WebGPU if available)
      const [clsProc, clsMod] = await Promise.all([
        AutoProcessor.from_pretrained(config.classifierModel),
        AutoModelForImageClassification.from_pretrained(
          config.classifierModel,
          {
            device: classifierDevice,
            dtype: "fp32" as const,
            progress_callback: progressClassifier as unknown as (
              progress: unknown,
            ) => void,
          },
        ),
      ]);

      console.log("[worker] Classifier loaded, patching processor...");
      patchProcessorSize(clsProc);
      classifierProcessor = clsProc;
      classifierModel = clsMod;

      loadedConfig = config;
      console.log("[worker] All models loaded successfully");
      send({ type: "model-loaded" });
    } catch (err) {
      console.error("[worker] Model loading error:", err);
      send({
        type: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // ── Run inference ────────────────────────────────────────────────────────
  if (data.type === "run-inference") {
    if (
      !detectorModel ||
      !detectorProcessor ||
      !classifierModel ||
      !classifierProcessor ||
      !loadedConfig
    ) {
      send({ type: "error", message: "Models not loaded" });
      return;
    }

    const { imageSrc, imageIndex } = data;
    const config = loadedConfig;
    const timestampedId = `${config.id}:${Date.now()}`;

    try {
      send({ type: "status", status: "detecting" });

      // Load & preprocess image for detection
      console.log("[worker] Loading image for detection...");
      const rawImage = await RawImage.read(imageSrc);
      console.log(
        "[worker] Image loaded:",
        rawImage.width,
        "x",
        rawImage.height,
      );

      const detInputs = await detectorProcessor(rawImage);
      console.log("[worker] Detector inputs keys:", Object.keys(detInputs));
      for (const [key, val] of Object.entries(detInputs)) {
        const t = val as {
          dims?: number[];
          type?: string;
          data?: Float32Array;
        };
        if (t?.dims) {
          console.log(
            `[worker]   ${key}: dims=${JSON.stringify(t.dims)} dtype=${t.type}`,
          );
        }
        if (key === "pixel_values" && t?.data) {
          const d = t.data;
          let min = Infinity,
            max = -Infinity,
            sum = 0;
          for (let i = 0; i < d.length; i++) {
            if (d[i] < min) min = d[i];
            if (d[i] > max) max = d[i];
            sum += d[i];
          }
          const mean = sum / d.length;
          console.log(
            `[worker] pixel_values stats: min=${min.toFixed(4)} max=${max.toFixed(4)} mean=${mean.toFixed(4)} length=${d.length}`,
          );
          // First 10 values for comparison with Python
          console.log(
            "[worker] pixel_values first 10:",
            Array.from(d.slice(0, 10)).map((v) => v.toFixed(4)),
          );
        }
      }

      // Run detector model
      console.log("[worker] Running detector model...");
      const detOutputs = await detectorModel(detInputs);
      console.log("[worker] Detector output keys:", Object.keys(detOutputs));
      for (const [key, val] of Object.entries(detOutputs)) {
        const t = val as {
          dims?: number[];
          type?: string;
          data?: Float32Array;
        };
        if (t?.dims) {
          console.log(
            `[worker]   ${key}: dims=${JSON.stringify(t.dims)} dtype=${t.type}`,
          );
        }
        if (key === "logits" && t?.data) {
          const scores = Array.from(t.data).map(
            (v: number) => 1 / (1 + Math.exp(-v)),
          ); // sigmoid
          const sorted = [...scores].sort((a, b) => b - a);
          console.log("[worker] Top 10 sigmoid scores:", sorted.slice(0, 10));
          console.log(
            "[worker] Scores > 0.01:",
            scores.filter((s: number) => s > 0.01).length,
          );
        }
      }

      // Post-process detections
      // RT-DETR uses sigmoid (no background class), so pass is_zero_shot=true
      const numClasses = detOutputs.logits.dims[2];
      const useSigmoid = numClasses === 1;

      // Get boxes in model input space (640x640), then scale to original
      // image dimensions ourselves — matching the Python CLI approach.
      // post_process with null target_sizes returns normalized [0,1] boxes.
      console.log(
        "[worker] Post-processing with threshold:",
        config.detectorThreshold,
        "sigmoid:",
        useSigmoid,
      );
      const processed = (
        detectorProcessor.image_processor ?? detectorProcessor
      ).post_process_object_detection(
        detOutputs,
        config.detectorThreshold,
        null, // get normalized boxes
        useSigmoid,
      ) as PostProcessedDetection[];

      // Scale normalized boxes from padded model space to original image coords.
      // The model input is 640x640 (padded). The image was resized preserving
      // aspect ratio, so we need to scale through the resized dimensions.
      const modelW = detInputs.pixel_values.dims[3];
      const modelH = detInputs.pixel_values.dims[2];
      const resizeScale = Math.min(
        modelW / rawImage.width,
        modelH / rawImage.height,
      );
      const resizedW = rawImage.width * resizeScale;
      const resizedH = rawImage.height * resizeScale;
      const scaleX = rawImage.width / resizedW;
      const scaleY = rawImage.height / resizedH;

      console.log(
        "[worker] Model input:",
        modelW,
        "x",
        modelH,
        "resized:",
        resizedW.toFixed(0),
        "x",
        resizedH.toFixed(0),
        "scale:",
        scaleX.toFixed(3),
        "x",
        scaleY.toFixed(3),
      );

      // Convert normalized boxes to original image pixel coordinates
      for (const det of processed) {
        for (let i = 0; i < det.boxes.length; i++) {
          const [x0, y0, x1, y1] = det.boxes[i];
          det.boxes[i] = [
            x0 * modelW * scaleX,
            y0 * modelH * scaleY,
            x1 * modelW * scaleX,
            y1 * modelH * scaleY,
          ];
        }
      }

      console.log(
        "[worker] Post-processed detections:",
        JSON.stringify(processed),
      );

      const id2label = detectorModel.config?.id2label ?? {};
      const detections = processed[0];
      console.log(
        "[worker] Detections count:",
        detections?.boxes?.length ?? 0,
        "id2label keys:",
        Object.keys(id2label).length,
      );

      if (!detections || !detections.boxes || detections.boxes.length === 0) {
        console.log("[worker] No detections above threshold");
        send({
          type: "result",
          imageIndex,
          modelConfigId: timestampedId,
          result: emptyResult(config),
        });
        return;
      }

      console.log("[worker] Found", detections.boxes.length, "detections");

      const inferenceId = `mini-${Date.now()}`;

      // Build all boxes from detection results (before any classification)
      const boxes: InferenceBox[] = [];
      const scores: number[] = [];
      const classifications: string[] = [];
      const topNResults: Array<Array<{ score: number; label: string }>> = [];

      for (let i = 0; i < detections.boxes.length; i++) {
        const [xmin, ymin, xmax, ymax] = detections.boxes[i];
        const score = detections.scores[i];
        const classIdx = detections.classes[i];
        const detLabel = id2label[classIdx] ?? `class_${classIdx}`;

        console.log(
          `[worker] Detection ${i}: label=${detLabel} score=${score.toFixed(3)} box=[${xmin.toFixed(0)},${ymin.toFixed(0)},${xmax.toFixed(0)},${ymax.toFixed(0)}]`,
        );

        boxes.push({
          topX: xmin,
          topY: ymin,
          bottomX: xmax,
          bottomY: ymax,
          inferenceId,
          boxId: String(i),
          classId: detLabel,
          label: detLabel,
          isVerified: false,
        });
        scores.push(score);
        classifications.push(""); // sentinel: not yet classified
        topNResults.push([]);
      }

      // Send partial result: all boxes visible, no classifications yet
      send({
        type: "partial-result",
        imageIndex,
        modelConfigId: timestampedId,
        result: {
          scores: [...scores],
          classifications: [...classifications],
          boxes: [...boxes],
          topN: [...topNResults],
          overlapping: boxes.map(() => false),
          overlappingIndices: boxes.map(() => 0),
          labelOccurrence: {},
          totalBoxes: boxes.length,
          models: [
            { name: config.detectorModel, version: "1.0" },
            { name: config.classifierModel, version: "1.0" },
          ],
          completedAt: "",
          isActive: true,
          minBoxSize: config.minBoxSize,
        },
      });

      send({ type: "status", status: "classifying" });

      // Decode the full image once for region cropping
      const imageBlob = await (await fetch(imageSrc)).blob();
      const bitmap = await createImageBitmap(imageBlob);

      await classifyBoxes(
        bitmap,
        boxes,
        scores,
        classifications,
        topNResults,
        config,
        imageIndex,
        timestampedId,
      );

      bitmap.close();

      const result: InferenceResult = {
        scores,
        classifications,
        boxes,
        topN: topNResults,
        overlapping: boxes.map(() => false),
        overlappingIndices: boxes.map(() => 0),
        labelOccurrence: buildLabelOccurrence(classifications),
        totalBoxes: boxes.length,
        models: [
          { name: config.detectorModel, version: "1.0" },
          { name: config.classifierModel, version: "1.0" },
        ],
        completedAt: new Date().toISOString(),
        isActive: true,
        minBoxSize: config.minBoxSize,
      };

      console.log("[worker] Inference complete:", boxes.length, "boxes");
      send({
        type: "result",
        imageIndex,
        modelConfigId: timestampedId,
        result,
      });
    } catch (err) {
      console.error("[worker] Inference error:", err);
      send({
        type: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // ── Classify only (edited boxes) ─────────────────────────────────────────
  if (data.type === "run-classify-only") {
    if (!classifierModel || !classifierProcessor || !loadedConfig) {
      send({ type: "error", message: "Models not loaded" });
      return;
    }

    const { imageSrc, imageIndex, boxes: inputBoxes, modelConfigId } = data;
    const config = loadedConfig;

    try {
      send({ type: "status", status: "classifying" });

      const inferenceId = `mini-edited-${Date.now()}`;
      const boxes: InferenceBox[] = inputBoxes.map((b, i) => ({
        topX: b.topX,
        topY: b.topY,
        bottomX: b.bottomX,
        bottomY: b.bottomY,
        inferenceId,
        boxId: `edited-${i}`,
        classId: "",
        label: "",
        isVerified: false,
      }));
      const scores = boxes.map(() => 1);
      const classifications = boxes.map(() => "");
      const topNResults: Array<Array<{ score: number; label: string }>> =
        boxes.map(() => []);

      // Send partial result showing boxes before classification
      send({
        type: "partial-result",
        imageIndex,
        modelConfigId,
        result: {
          scores: [...scores],
          classifications: [...classifications],
          boxes: [...boxes],
          topN: [...topNResults],
          overlapping: boxes.map(() => false),
          overlappingIndices: boxes.map(() => 0),
          labelOccurrence: {},
          totalBoxes: boxes.length,
          models: [
            { name: config.detectorModel, version: "1.0" },
            { name: config.classifierModel, version: "1.0" },
          ],
          completedAt: "",
          isActive: true,
          minBoxSize: config.minBoxSize,
        },
      });

      const imageBlob = await (await fetch(imageSrc)).blob();
      const bitmap = await createImageBitmap(imageBlob);

      await classifyBoxes(
        bitmap,
        boxes,
        scores,
        classifications,
        topNResults,
        config,
        imageIndex,
        modelConfigId,
      );

      bitmap.close();

      const result: InferenceResult = {
        scores,
        classifications,
        boxes,
        topN: topNResults,
        overlapping: boxes.map(() => false),
        overlappingIndices: boxes.map(() => 0),
        labelOccurrence: buildLabelOccurrence(classifications),
        totalBoxes: boxes.length,
        models: [
          { name: config.detectorModel, version: "1.0" },
          { name: config.classifierModel, version: "1.0" },
        ],
        completedAt: new Date().toISOString(),
        isActive: true,
        minBoxSize: config.minBoxSize,
      };

      console.log("[worker] Classify-only complete:", boxes.length, "boxes");
      send({ type: "result", imageIndex, modelConfigId, result });
    } catch (err) {
      console.error("[worker] Classify-only error:", err);
      send({
        type: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }
});

// ---------------------------------------------------------------------------
// Shared classification helper
// ---------------------------------------------------------------------------

async function classifyBoxes(
  bitmap: ImageBitmap,
  boxes: InferenceBox[],
  scores: number[],
  classifications: string[],
  topNResults: Array<Array<{ score: number; label: string }>>,
  config: ModelConfig,
  imageIndex: number,
  modelConfigId: string,
): Promise<void> {
  for (let i = 0; i < boxes.length; i++) {
    const { topX: xmin, topY: ymin, bottomX: xmax, bottomY: ymax } = boxes[i];

    let cropUrl: string | null = null;
    try {
      cropUrl = await cropRegion(bitmap, xmin, ymin, xmax, ymax);

      const cropImage = await RawImage.read(cropUrl);
      const clsInputs = await classifierProcessor(cropImage);
      const clsOutputs = await classifierModel(clsInputs);

      const logits = clsOutputs.logits[0];
      const probs = new Tensor(
        "float32",
        softmax(logits.data as Float32Array),
        logits.dims,
      );
      const [topValues, topIndices] = await topk(probs, config.classifierTopK);

      const clsId2label = classifierModel.config?.id2label ?? {};
      const topValList = topValues.tolist() as number[];
      const topIdxList = topIndices.tolist() as number[];

      const classResults = topIdxList.map((idx: number, j: number) => ({
        label: clsId2label[idx] ?? `LABEL_${idx}`,
        score: topValList[j],
      }));

      const topLabel = classResults[0]?.label ?? boxes[i].classId;
      console.log(
        `[worker] Classification ${i}: top=${topLabel} (${classResults[0]?.score.toFixed(3)})`,
      );

      classifications[i] = topLabel;
      topNResults[i] = classResults;
      boxes[i] = { ...boxes[i], label: topLabel };

      send({
        type: "partial-result",
        imageIndex,
        modelConfigId,
        result: {
          scores: [...scores],
          classifications: [...classifications],
          boxes: [...boxes],
          topN: [...topNResults],
          overlapping: boxes.map(() => false),
          overlappingIndices: boxes.map(() => 0),
          labelOccurrence: buildLabelOccurrence(classifications),
          totalBoxes: boxes.length,
          models: [
            { name: config.detectorModel, version: "1.0" },
            { name: config.classifierModel, version: "1.0" },
          ],
          completedAt: "",
          isActive: true,
          minBoxSize: config.minBoxSize,
        },
      });
    } finally {
      if (cropUrl) URL.revokeObjectURL(cropUrl);
    }
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildLabelOccurrence(classifications: string[]): {
  [key: string]: number;
} {
  const labelOccurrence: { [key: string]: number } = {};
  for (const label of classifications) {
    if (label !== "") {
      labelOccurrence[label] = (labelOccurrence[label] ?? 0) + 1;
    }
  }
  return labelOccurrence;
}

function emptyResult(config: ModelConfig): InferenceResult {
  return {
    scores: [],
    classifications: [],
    boxes: [],
    topN: [],
    overlapping: [],
    overlappingIndices: [],
    labelOccurrence: {},
    totalBoxes: 0,
    models: [
      { name: config.detectorModel, version: "1.0" },
      { name: config.classifierModel, version: "1.0" },
    ],
    completedAt: new Date().toISOString(),
    isActive: true,
    minBoxSize: config.minBoxSize,
  };
}

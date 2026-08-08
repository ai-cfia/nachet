// This file runs as a Web Worker module bundled by Vite.

import {
  AutoProcessor,
  AutoModelForImageClassification,
  RawImage,
  Tensor,
  softmax,
  topk,
  env,
} from "@huggingface/transformers";
import type { ModelConfig, WorkerInMessage, WorkerOutMessage } from "./models";
import { huggingFaceFileUrl } from "./models";
import type {
  BoxTaxonomy,
  InferenceResult,
  InferenceBox,
  RankedPrediction,
} from "@common/types";
import {
  loadDetector,
  runDetector,
  isDetectorReady,
  patchProcessorSize,
} from "./detector";
import { createSerialQueue } from "./serialQueue";
import { computeCam } from "./cam";
import { aggregateTaxonomyProbabilities } from "./taxonomy";

// Class Activation Mapping runs only when the loaded classifier exposes the
// `swin_layernorm` output (the patched 101spp model); otherwise it's skipped.
// One heatmap is produced per top-K class so the UI can show which regions
// drive each candidate species.

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
// Worker-specific helpers
// ---------------------------------------------------------------------------

/** Send a typed message from the worker to the main thread. */
const send = (msg: WorkerOutMessage): void => {
  (
    globalThis as unknown as { postMessage(msg: WorkerOutMessage): void }
  ).postMessage(msg);
};

type DeviceType = "webgpu" | "wasm";

/** Detect whether WebGPU is available in this worker context. */
const getDevice = async (): Promise<DeviceType> => {
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
};

/** Crop a rectangular region from an ImageBitmap using OffscreenCanvas. */
const cropRegion = async (
  bitmap: ImageBitmap,
  xmin: number,
  ymin: number,
  xmax: number,
  ymax: number,
): Promise<string> => {
  const w = Math.max(1, Math.round(xmax - xmin));
  const h = Math.max(1, Math.round(ymax - ymin));
  const canvas = new OffscreenCanvas(w, h);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("OffscreenCanvas 2D context unavailable");
  ctx.drawImage(bitmap, Math.round(xmin), Math.round(ymin), w, h, 0, 0, w, h);
  const blob = await canvas.convertToBlob({ type: "image/jpeg", quality: 0.9 });
  return URL.createObjectURL(blob);
};

// ---------------------------------------------------------------------------
// Pipeline state
// ---------------------------------------------------------------------------

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

const makeProgressCallback = (phase: "detector" | "classifier") => {
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
};

// ---------------------------------------------------------------------------
// Message handler
// ---------------------------------------------------------------------------

// Serialize every worker operation. Without this, a `load-models` message
// could run concurrently with an in-flight `run-inference` and release ORT
// sessions that inference is still using — which surfaces as a "function
// signature mismatch" crash. The queue makes a model switch wait for the
// current inference to finish before tearing anything down.
const runSerial = createSerialQueue();

const handleMessage = async (data: WorkerInMessage): Promise<void> => {
  // ── Load models ──────────────────────────────────────────────────────────
  if (data.type === "load-models") {
    const config = data.config;
    const device = await getDevice();
    const classifierDevice = device;
    const progressDetector = makeProgressCallback("detector");
    const progressClassifier = makeProgressCallback("classifier");

    try {
      send({ type: "status", status: "loading-model" });

      console.log("[worker] Loading detector model:", config.detectorModel);
      console.log(
        "[worker] Loading classifier model:",
        config.classifierModel,
        "device:",
        classifierDevice,
      );

      // Detector loading is delegated to the detector module, which handles
      // both the SAM 3 (text-promptable) and closed-vocabulary paths and frees
      // the other kind's memory before loading its own.
      await loadDetector(config, {
        transformersProgress: progressDetector as unknown as (
          info: unknown,
        ) => void,
        sam3Progress: (info) => {
          send({
            type: "model-progress",
            name: `detector: ${info.name}`,
            progress: info.progress,
          });
        },
      });

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
      // ORT-Web sometimes throws bare numeric pointers into wasm memory
      // (e.g. `25954464`) instead of Error objects. When that happens, dump
      // the raw value, its type, and any properties so we can at least see
      // what we're dealing with — `String(err)` alone is useless.
      console.error("[worker] Model loading error (raw):", err);
      console.error("[worker]   typeof:", typeof err);
      try {
        const eAny = err as { name?: string; message?: string; stack?: string };
        console.error("[worker]   err.name:", eAny?.name);
        console.error("[worker]   err.message:", eAny?.message);
        console.error("[worker]   err.stack:", eAny?.stack);
        console.error(
          "[worker]   keys:",
          err && typeof err === "object" ? Object.keys(err) : "(not object)",
        );
      } catch {
        // ignore — diagnostics only
      }
      const message =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "message" in err
            ? String((err as { message: unknown }).message)
            : String(err);
      send({ type: "error", message });
    }
  }

  // ── Run inference ────────────────────────────────────────────────────────
  if (data.type === "run-inference") {
    // Validation differs by detector kind — the detector module knows how to
    // check readiness for each path (SAM 3 readiness is managed internally).
    if (!classifierModel || !classifierProcessor || !loadedConfig) {
      send({ type: "error", message: "Models not loaded" });
      return;
    }
    if (!isDetectorReady(loadedConfig)) {
      send({ type: "error", message: "Detector not loaded" });
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

      // Detector inference is delegated to the detector module. Both paths
      // return `detections` + `labelForClass` so the box-building loop below
      // can treat them uniformly.
      const { detections, labelForClass } = await runDetector(
        config,
        imageSrc,
        rawImage,
        data.prompt,
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
      const topNResults: RankedPrediction[][] = [];
      const taxonomyResults: Array<BoxTaxonomy | undefined> = [];

      for (let i = 0; i < detections.boxes.length; i++) {
        const [xmin, ymin, xmax, ymax] = detections.boxes[i];
        const score = detections.scores[i];
        const classIdx = detections.classes[i];
        const detLabel = labelForClass(classIdx);

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
          bboxSource: "model",
        });
        scores.push(score);
        classifications.push(""); // sentinel: not yet classified
        topNResults.push([]);
        taxonomyResults.push(undefined);
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
        taxonomyResults,
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
        taxonomy: availableTaxonomy(taxonomyResults),
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
      // Same dance as load-models: ORT-Web sometimes throws bare wasm
      // pointers (e.g. `2397765560`) instead of Error objects. Dig out
      // whatever we can.
      console.error("[worker] Inference error (raw):", err);
      console.error("[worker]   typeof:", typeof err);
      try {
        const eAny = err as { name?: string; message?: string; stack?: string };
        console.error("[worker]   err.name:", eAny?.name);
        console.error("[worker]   err.message:", eAny?.message);
        console.error("[worker]   err.stack:", eAny?.stack);
        console.error(
          "[worker]   keys:",
          err && typeof err === "object" ? Object.keys(err) : "(not object)",
        );
      } catch {
        // ignore — diagnostics only
      }
      const message =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "message" in err
            ? String((err as { message: unknown }).message)
            : String(err);
      send({ type: "error", message });
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
        bboxSource: "model" as const,
      }));
      const scores = boxes.map(() => 1);
      const classifications = boxes.map(() => "");
      const topNResults: RankedPrediction[][] = boxes.map(() => []);
      const taxonomyResults: Array<BoxTaxonomy | undefined> = boxes.map(
        () => undefined,
      );

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
        taxonomyResults,
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
        taxonomy: availableTaxonomy(taxonomyResults),
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
};

// The only origin we accept messages from is our own. Dedicated-worker
// messages posted by the host page carry an empty origin, which we also allow;
// anything else is rejected. The explicit `event.origin` comparisons below are
// what CodeQL's missing-origin-verification query looks for.
const EXPECTED_MESSAGE_ORIGIN = self.location.origin;

// Enqueue each message so it runs strictly after the previous one settles.
addEventListener("message", (event: MessageEvent) => {
  if (event.origin !== "" && event.origin !== EXPECTED_MESSAGE_ORIGIN) {
    console.warn(
      "[worker] Ignoring message from untrusted origin:",
      event.origin,
    );
    return;
  }
  const data = event.data as WorkerInMessage;
  runSerial(() => handleMessage(data));
});

// ---------------------------------------------------------------------------
// Shared classification helper
// ---------------------------------------------------------------------------

const classifyBoxes = async (
  bitmap: ImageBitmap,
  boxes: InferenceBox[],
  scores: number[],
  classifications: string[],
  topNResults: RankedPrediction[][],
  taxonomyResults: Array<BoxTaxonomy | undefined>,
  config: ModelConfig,
  imageIndex: number,
  modelConfigId: string,
): Promise<void> => {
  for (let i = 0; i < boxes.length; i++) {
    const { topX: xmin, topY: ymin, bottomX: xmax, bottomY: ymax } = boxes[i];

    let cropUrl: string | null = null;
    try {
      cropUrl = await cropRegion(bitmap, xmin, ymin, xmax, ymax);

      const cropImage = await RawImage.read(cropUrl);
      const clsInputs = await classifierProcessor(cropImage);

      // Run the underlying ORT session directly (instead of the high-level
      // classifierModel(clsInputs)) so we can also read the intermediate
      // `swin_layernorm` output for DFF. The transformers.js wrapper keeps only
      // recognized outputs (logits) and drops the rest. logits are identical.
      const session = classifierModel.sessions.model;
      const pv = clsInputs.pixel_values;
      const rawOut = await session.run({ pixel_values: pv.ort_tensor ?? pv });

      // squeeze batch dim to match the previous `clsOutputs.logits[0]` shape
      const logits = {
        data: rawOut.logits.data as Float32Array,
        dims: [rawOut.logits.dims[rawOut.logits.dims.length - 1]],
      };
      const probabilities = softmax(logits.data);
      const probs = new Tensor("float32", probabilities, logits.dims);
      const [topValues, topIndices] = await topk(probs, config.classifierTopK);

      const clsId2label = classifierModel.config?.id2label ?? {};
      const topValList = topValues.tolist() as number[];
      // tolist() of an int64 index tensor yields BigInt; coerce to Number so
      // downstream arithmetic (CAM weight indexing) doesn't mix BigInt + Number.
      const topIdxList = (topIndices.tolist() as Array<number | bigint>).map(
        Number,
      );

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
      taxonomyResults[i] = aggregateTaxonomyProbabilities(
        probabilities,
        clsId2label,
        undefined,
        3,
        classResults.map(({ label }) => label),
      );
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
          taxonomy: availableTaxonomy(taxonomyResults),
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

      // ── Class Activation Mapping ─────────────────────────────────────────
      // Only when the classifier declares head weights (`classifierHeadFile`)
      // and exposes `swin_layernorm` (1, tokens, channels) — i.e. the patched
      // model. One heatmap per top-K class so the UI can show which regions
      // drive each candidate species. Streamed per box so maps arrive after
      // each seed is classified.
      const headFile = config.classifierHeadFile;
      const featTensor = rawOut.swin_layernorm as
        | { data?: Float32Array; dims?: number[] }
        | undefined;
      if (headFile && featTensor?.data && featTensor.dims?.length === 3) {
        try {
          const [, tokens, channels] = featTensor.dims;
          const cam = await computeCam(
            featTensor.data,
            tokens,
            channels,
            topIdxList,
            huggingFaceFileUrl(config.classifierModel, headFile),
          );
          send({
            type: "cam-result",
            imageIndex,
            modelConfigId,
            boxId: boxes[i].boxId,
            grid: cam.grid,
            classes: topIdxList.map((idx: number, j: number) => ({
              classIndex: idx,
              label: classResults[j]?.label ?? `LABEL_${idx}`,
              score: classResults[j]?.score ?? 0,
              heatmap: Array.from(cam.maps[j]),
            })),
          });
        } catch (e) {
          console.warn("[worker] CAM failed for box", i, e);
        }
      }
    } finally {
      if (cropUrl) URL.revokeObjectURL(cropUrl);
    }
  }
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const buildLabelOccurrence = (
  classifications: string[],
): {
  [key: string]: number;
} => {
  const labelOccurrence: { [key: string]: number } = {};
  for (const label of classifications) {
    if (label !== "") {
      labelOccurrence[label] = (labelOccurrence[label] ?? 0) + 1;
    }
  }
  return labelOccurrence;
};

const availableTaxonomy = (
  taxonomy: Array<BoxTaxonomy | undefined>,
): Array<BoxTaxonomy | undefined> | undefined =>
  taxonomy.some(Boolean) ? [...taxonomy] : undefined;

const emptyResult = (config: ModelConfig): InferenceResult => {
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
};

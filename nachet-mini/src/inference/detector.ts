// Detector loading and inference, split out of worker.ts.
//
// There are two detector paths:
//
//   1. text-promptable-segmentation (SAM 3) — a multi-component, text-
//      conditioned detector orchestrated via raw onnxruntime-web. The heavy
//      lifting lives in the sam3 module; this file just delegates to it.
//
//   2. object-detection (default) — a single-file closed-vocabulary model
//      (RT-DETR, DETR) loaded through transformers.js's
//      AutoModelForObjectDetection.
//
// The classifier still lives in worker.ts — splitting it out is a later PR.

import {
  AutoProcessor,
  AutoModelForObjectDetection,
} from "@huggingface/transformers";
import type { RawImage } from "@huggingface/transformers";
import type { ModelConfig } from "./models";
import { loadSam3, runSam3, unloadSam3 } from "./sam3";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Post-processed detections — the shared shape both detector paths produce. */
export interface PostProcessedDetection {
  boxes: number[][];
  classes: number[];
  scores: number[];
}

/** Progress callbacks the worker forwards to the main thread during load. */
export interface DetectorLoadCallbacks {
  /** transformers.js `progress_callback` for the closed-vocabulary detector. */
  transformersProgress: (info: unknown) => void;
  /** Aggregate progress for the SAM 3 multi-component load. */
  sam3Progress: (info: { name: string; progress: number }) => void;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Only the closed-vocabulary path uses these; the SAM 3 path keeps its own
// sessions inside the sam3 module.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let detectorModel: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let detectorProcessor: any = null;

// ---------------------------------------------------------------------------
// Processor size patching
// ---------------------------------------------------------------------------

/**
 * Some HuggingFace models (e.g. RT-DETR from cfia-ai-lab) use
 * `{ max_height, max_width }` in their preprocessor_config.json `size` field.
 * transformers.js doesn't support this format, so we convert it to
 * `{ longest_edge }` which preserves aspect ratio.
 *
 * Exported because the classifier load in worker.ts patches its processor the
 * same way.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const patchProcessorSize = (processor: any): void => {
  // AutoProcessor wraps an image_processor; try both paths
  const imageProcessor = processor?.image_processor ?? processor;
  if (!imageProcessor?.size) {
    console.log("[detector] No image processor size to patch");
    return;
  }

  const size = imageProcessor.size;
  console.log("[detector] Processor size config:", JSON.stringify(size));

  if (size.max_height !== undefined && size.max_width !== undefined) {
    const longest = Math.min(size.max_height, size.max_width);
    console.log(
      `[detector] Patching processor size: {max_height: ${size.max_height}, max_width: ${size.max_width}} → {longest_edge: ${longest}}`,
    );
    imageProcessor.size = { longest_edge: longest };
  }
};

// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

/**
 * Load the detector described by `config`. Dispatches to the SAM 3 module for
 * text-promptable detectors, otherwise loads a closed-vocabulary model via
 * transformers.js.
 */
export const loadDetector = async (
  config: ModelConfig,
  callbacks: DetectorLoadCallbacks,
): Promise<void> => {
  // WebGPU has precision issues with detection models — always use WASM.
  const detectorDevice = "wasm" as const;

  if (config.detectorKind === "text-promptable-segmentation") {
    console.log("[detector] Loading SAM 3 detector via sam3 module");
    // Free any previously-loaded closed-vocabulary detector first so we don't
    // hold two detectors in memory while SAM 3's components load.
    detectorModel = null;
    detectorProcessor = null;
    // SAM 3's three components — vision encoder, text encoder, decoder — are
    // loaded inside the sam3 module. We forward its progress events.
    await loadSam3(config, callbacks.sam3Progress);
    return;
  }

  // Closed-vocabulary detector path (RT-DETR, DETR, existing behavior).
  //
  // Free any previously-loaded SAM 3 sessions BEFORE allocating the new
  // detector, so we don't hold SAM 3's (large) sessions and the new detector
  // in memory at the same time — keeps peak memory down when switching
  // detectors.
  await unloadSam3();

  const [detProc, detMod] = await Promise.all([
    AutoProcessor.from_pretrained(config.detectorModel),
    AutoModelForObjectDetection.from_pretrained(config.detectorModel, {
      device: detectorDevice,
      dtype: "fp32" as const,
      model_file_name: config.detectorModelFileName ?? "model",
      progress_callback: callbacks.transformersProgress as unknown as (
        progress: unknown,
      ) => void,
    }),
  ]);

  console.log("[detector] Detector loaded, patching processor...");
  patchProcessorSize(detProc);
  detectorProcessor = detProc;
  detectorModel = detMod;
  console.log(
    "[detector] Detector id2label:",
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    JSON.stringify((detMod.config as any)?.id2label ?? {}),
  );
};

/**
 * Whether the detector for `config` is ready to run inference. SAM 3 readiness
 * is managed inside the sam3 module (runDetector throws if it isn't loaded),
 * so only the closed-vocabulary path is checked here.
 */
export const isDetectorReady = (config: ModelConfig): boolean => {
  if (config.detectorKind === "text-promptable-segmentation") return true;
  return !!detectorModel && !!detectorProcessor;
};

// ---------------------------------------------------------------------------
// Inference
// ---------------------------------------------------------------------------

/**
 * Run the detector over `rawImage`. Both paths return `detections` plus a
 * `labelForClass` mapper so the worker's box-building loop can treat them
 * uniformly.
 */
export const runDetector = async (
  config: ModelConfig,
  imageSrc: string,
  rawImage: RawImage,
  prompt: string | null | undefined,
): Promise<{
  detections: PostProcessedDetection;
  labelForClass: (classIdx: number) => string;
}> => {
  if (config.detectorKind === "text-promptable-segmentation") {
    // SAM 3 path — the sam3 module handles preprocessing, inference, and
    // post-processing.
    const concept = prompt?.trim() || "seed";
    console.log(
      `[detector] Running SAM 3 detector with prompt: "${concept}", threshold: ${config.detectorThreshold}`,
    );
    const detections = await runSam3(
      imageSrc,
      concept,
      config.detectorThreshold,
      rawImage.width,
      rawImage.height,
    );
    console.log(
      `[detector] SAM 3 returned ${detections.boxes.length} detections`,
    );
    // Open-vocabulary — every detection gets the prompt as its label.
    return { detections, labelForClass: () => concept };
  }

  // Closed-vocabulary detector path (RT-DETR, DETR, etc.) — transformers.js.
  if (!detectorModel || !detectorProcessor) {
    throw new Error("Detector model is null in closed-vocabulary path");
  }

  const detInputs = await detectorProcessor(rawImage);
  const detOutputs = await detectorModel(detInputs);
  console.log("[detector] Detector output keys:", Object.keys(detOutputs));
  for (const [key, val] of Object.entries(detOutputs)) {
    const t = val as {
      dims?: number[];
      type?: string;
      data?: Float32Array;
    };
    if (t?.dims) {
      console.log(
        `[detector]   ${key}: dims=${JSON.stringify(t.dims)} dtype=${t.type}`,
      );
    }
    if (key === "logits" && t?.data) {
      const scores = Array.from(t.data).map(
        (v: number) => 1 / (1 + Math.exp(-v)),
      ); // sigmoid
      const sorted = [...scores].sort((a, b) => b - a);
      console.log("[detector] Top 10 sigmoid scores:", sorted.slice(0, 10));
      console.log(
        "[detector] Scores > 0.01:",
        scores.filter((s: number) => s > 0.01).length,
      );
    }
  }

  // Post-process detections.
  // RT-DETR uses sigmoid (no background class), so pass is_zero_shot=true.
  const numClasses = detOutputs.logits.dims[2];
  const useSigmoid = numClasses === 1;

  // Get boxes in model input space (640x640), then scale to original image
  // dimensions ourselves — matching the Python CLI approach. post_process with
  // null target_sizes returns normalized [0,1] boxes.
  console.log(
    "[detector] Post-processing with threshold:",
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
    "[detector] Model input:",
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

  // Convert normalized boxes to original image pixel coordinates.
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
    "[detector] Post-processed detections:",
    JSON.stringify(processed),
  );

  const id2label = detectorModel.config?.id2label ?? {};
  const detections = processed[0];
  const labelForClass = (classIdx: number): string =>
    id2label[classIdx] ?? `class_${classIdx}`;
  console.log(
    "[detector] Detections count:",
    detections?.boxes?.length ?? 0,
    "id2label keys:",
    Object.keys(id2label).length,
  );

  return { detections, labelForClass };
};

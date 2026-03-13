// This file runs as a Web Worker module bundled by Vite.
// The tsconfig targets DOM lib; Vite correctly re-targets the Worker runtime.
// Worker-specific globals (postMessage, addEventListener) are typed via the
// DOM lib, which is close enough — small casts are isolated to helpers below.

import { pipeline, env } from "@huggingface/transformers";
import type { ModelConfig, WorkerInMessage, WorkerOutMessage } from "./models";
import type { InferenceResult, InferenceBox } from "@common/types";

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

env.useBrowserCache = true;
env.allowRemoteModels = true;
env.allowLocalModels = true;

// ---------------------------------------------------------------------------
// Types for transformers.js output
// ---------------------------------------------------------------------------

interface DetectionBox {
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
}

interface DetectionItem {
  label: string;
  score: number;
  box: DetectionBox;
}

interface ClassificationItem {
  label: string;
  score: number;
}

// Callable pipeline interface — the object returned by pipeline() is callable.
// We use this narrow type instead of `any` to preserve call-site safety.
interface CallablePipeline {
  (input: string, options?: Record<string, unknown>): Promise<unknown>;
}

// ---------------------------------------------------------------------------
// Worker-specific helpers
// ---------------------------------------------------------------------------

/** Send a typed message from the worker to the main thread. */
function send(msg: WorkerOutMessage): void {
  // DOM lib types globalThis.postMessage as Window.postMessage (requiring targetOrigin).
  // In a worker context the signature is postMessage(msg, transfer?).
  // We cast through the narrow interface matching the worker's actual API.
  (
    globalThis as unknown as { postMessage(msg: WorkerOutMessage): void }
  ).postMessage(msg);
}

/** Detect whether WebGPU is available in this worker context. */
function getDevice(): string {
  try {
    if (typeof navigator !== "undefined" && "gpu" in (navigator as object)) {
      return "webgpu";
    }
  } catch {
    // navigator not available — fall through to WASM
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
// Pipeline state
// ---------------------------------------------------------------------------

let detector: CallablePipeline | null = null;
let classifier: CallablePipeline | null = null;
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
      // Throttle to ~10 updates/sec; always send 100% completion
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
    const device = getDevice();

    try {
      send({ type: "status", status: "loading-model" });

      detector = (await pipeline("object-detection", config.detectorModel, {
        device,
        dtype: "fp32",
        progress_callback: makeProgressCallback("detector") as unknown as (
          progress: unknown,
        ) => void,
      })) as unknown as CallablePipeline;

      classifier = (await pipeline(
        "image-classification",
        config.classifierModel,
        {
          device,
          dtype: "fp32",
          progress_callback: makeProgressCallback("classifier") as unknown as (
            progress: unknown,
          ) => void,
        },
      )) as unknown as CallablePipeline;

      loadedConfig = config;
      send({ type: "model-loaded" });
    } catch (err) {
      send({
        type: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // ── Run inference ────────────────────────────────────────────────────────
  if (data.type === "run-inference") {
    if (!detector || !classifier || !loadedConfig) {
      send({ type: "error", message: "Models not loaded" });
      return;
    }

    const { imageSrc, imageIndex } = data;
    const config = loadedConfig;

    try {
      send({ type: "status", status: "detecting" });

      const rawDetections = (await detector(imageSrc, {
        threshold: config.detectorThreshold,
      })) as DetectionItem[];

      console.log("Raw detections:", rawDetections);

      if (!rawDetections || rawDetections.length === 0) {
        send({
          type: "result",
          imageIndex,
          result: emptyResult(config),
        });
        return;
      }

      send({ type: "status", status: "classifying" });

      // Decode the full image once for region cropping
      const imageBlob = await (await fetch(imageSrc)).blob();
      const bitmap = await createImageBitmap(imageBlob);

      const boxes: InferenceBox[] = [];
      const scores: number[] = [];
      const classifications: string[] = [];
      const topN: Array<Array<{ score: number; label: string }>> = [];
      const inferenceId = `mini-${Date.now()}`;

      for (let i = 0; i < rawDetections.length; i++) {
        const det = rawDetections[i];
        const { xmin, ymin, xmax, ymax } = det.box;

        let cropUrl: string | null = null;
        try {
          cropUrl = await cropRegion(bitmap, xmin, ymin, xmax, ymax);
          const rawClass = (await classifier(cropUrl, {
            topk: config.classifierTopK,
          })) as ClassificationItem[];

          const topLabel = rawClass[0]?.label ?? det.label;
          boxes.push({
            topX: xmin,
            topY: ymin,
            bottomX: xmax,
            bottomY: ymax,
            inferenceId,
            boxId: String(i),
            classId: det.label,
            label: topLabel,
            isVerified: false,
          });
          scores.push(det.score);
          classifications.push(topLabel);
          topN.push(rawClass.map((r) => ({ score: r.score, label: r.label })));
        } finally {
          if (cropUrl) URL.revokeObjectURL(cropUrl);
        }
      }

      bitmap.close();

      const labelOccurrence: { [key: string]: number } = {};
      for (const label of classifications) {
        labelOccurrence[label] = (labelOccurrence[label] ?? 0) + 1;
      }

      const result: InferenceResult = {
        scores,
        classifications,
        boxes,
        topN,
        overlapping: boxes.map(() => false),
        overlappingIndices: boxes.map(() => 0),
        labelOccurrence,
        totalBoxes: boxes.length,
        models: [
          { name: config.detectorModel, version: "1.0" },
          { name: config.classifierModel, version: "1.0" },
        ],
        completedAt: new Date().toISOString(),
        isActive: true,
      };

      send({ type: "result", imageIndex, result });
    } catch (err) {
      send({
        type: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
  };
}

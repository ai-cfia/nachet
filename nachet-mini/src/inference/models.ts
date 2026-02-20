import type { InferenceResult } from "@common/types";

export interface ModelConfig {
  id: string;
  /** HuggingFace model ID for object detection (must have ONNX weights) */
  detectorModel: string;
  /** HuggingFace model ID for image classification (must have ONNX weights) */
  classifierModel: string;
  /** Minimum detection confidence score [0, 1] */
  detectorThreshold: number;
  /** Number of top classification labels to keep per detected region */
  classifierTopK: number;
}

// ---------------------------------------------------------------------------
// Worker message protocol
// ---------------------------------------------------------------------------

export type WorkerInMessage =
  | { type: "load-models"; config: ModelConfig }
  | { type: "run-inference"; imageSrc: string; imageIndex: number };

export type WorkerOutMessage =
  | { type: "model-progress"; name: string; progress: number }
  | { type: "model-loaded" }
  | { type: "status"; status: "loading-model" | "detecting" | "classifying" }
  | { type: "result"; imageIndex: number; result: InferenceResult }
  | { type: "error"; message: string };

// ---------------------------------------------------------------------------
// Model registry
// ---------------------------------------------------------------------------

export const MODEL_PRESETS: ModelConfig[] = [
  {
    id: "detr-vit-general",
    detectorModel: "Xenova/detr-resnet-50",
    classifierModel: "Xenova/vit-base-patch16-224",
    detectorThreshold: 0.5,
    classifierTopK: 5,
  },
];

export const DEFAULT_MODEL = MODEL_PRESETS[0];

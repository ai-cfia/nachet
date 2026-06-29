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
  /** Optional ONNX filename for the detector (without .onnx), defaults to "model" */
  detectorModelFileName?: string;
  /** Minimum bounding-box size (longest dimension, px) for reliable classification */
  minBoxSize: number;
}

// ---------------------------------------------------------------------------
// Individual model entry types
// ---------------------------------------------------------------------------

export interface DetectorModelEntry {
  id: string;
  /** HuggingFace model ID for object detection (must have ONNX weights) */
  model: string;
  /** Minimum detection confidence score [0, 1] */
  threshold: number;
  /** Optional ONNX filename (without .onnx extension), defaults to "model" */
  modelFileName?: string;
}

export interface ClassifierModelEntry {
  id: string;
  /** HuggingFace model ID for image classification (must have ONNX weights) */
  model: string;
  /** Number of top classification labels to keep per detected region */
  topK: number;
  /** Minimum bounding-box size (longest dimension, px) for reliable classification */
  minBoxSize: number;
}

// ---------------------------------------------------------------------------
// Worker message protocol
// ---------------------------------------------------------------------------

export type WorkerInMessage =
  | { type: "load-models"; config: ModelConfig }
  | { type: "run-inference"; imageSrc: string; imageIndex: number }
  | {
      type: "run-classify-only";
      imageSrc: string;
      imageIndex: number;
      boxes: import("@common/types").BoxCoordinates[];
      modelConfigId: string;
    };

export type WorkerOutMessage =
  | { type: "model-progress"; name: string; progress: number }
  | { type: "model-loaded" }
  | { type: "status"; status: "loading-model" | "detecting" | "classifying" }
  | {
      type: "result";
      imageIndex: number;
      modelConfigId: string;
      result: InferenceResult;
    }
  | {
      type: "partial-result";
      imageIndex: number;
      modelConfigId: string;
      result: InferenceResult;
    }
  | {
      // Deep Feature Factorization concept heatmaps for one classified box.
      // Streamed separately from the classification result so the boxes render
      // immediately and DFF overlays arrive as each seed is factorized.
      type: "dff-result";
      imageIndex: number;
      modelConfigId: string;
      boxId: string;
      /** spatial grid side (e.g. 12 → 12×12 = 144 tokens). */
      grid: number;
      /** K concept heatmaps, each `grid*grid` floats normalized to [0, 1]. */
      heatmaps: number[][];
    }
  | { type: "error"; message: string };

// ---------------------------------------------------------------------------
// Model registries
// ---------------------------------------------------------------------------

export const DETECTOR_MODELS: DetectorModelEntry[] = [
  {
    id: "rt-detr-v2 64spp",
    model: "cfia-ai-lab/rtdetr_v2_r50vd-64spp-ft",
    threshold: 0.3,
    modelFileName: "model_patched",
  },
  {
    id: "rt-detr-v2 101spp",
    model: "cfia-ai-lab/rtdetr_v2_r50vd-101spp-ft",
    threshold: 0.8,
    modelFileName: "model_patched",
  },
  {
    id: "detr-resnet-50 0spp",
    model: "Xenova/detr-resnet-50",
    threshold: 0.5,
  },
];

export const CLASSIFIER_MODELS: ClassifierModelEntry[] = [
  {
    id: "swin-L 64spp",
    model: "cfia-ai-lab/swin-large-patch4-window12-384-in22k-64spp-ft",
    topK: 5,
    minBoxSize: 384,
  },
  {
    id: "swin-L 101spp",
    model: "cfia-ai-lab/swin-large-patch4-window12-384-in22k-101spp-ft",
    topK: 5,
    minBoxSize: 384,
  },
  {
    id: "swin-L 101spp DFF",
    // Same 101spp model, but this repo's onnx/model.onnx is the patched FP16
    // export that also outputs `swin_layernorm`. Selecting this entry surfaces
    // the Deep Feature Factorization UI (concept-map toggle + per-seed cutouts);
    // the plain "swin-L 101spp" entry above has no such output, so that UI stays
    // hidden for it.
    model: "cfia-ai-lab/swin-large-patch4-window12-384-in22k-101spp-ft-dff",
    topK: 5,
    minBoxSize: 384,
  },
  {
    id: "vit-base-224 0spp",
    model: "Xenova/vit-base-patch16-224",
    topK: 5,
    minBoxSize: 224,
  },
];

export const DEFAULT_DETECTOR = DETECTOR_MODELS[0];
export const DEFAULT_CLASSIFIER = CLASSIFIER_MODELS[0];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build the Hugging Face model page URL from a model ID. */
export const huggingFaceUrl = (modelId: string): string => {
  return `https://huggingface.co/${modelId}`;
};

/** Assemble a ModelConfig from independent detector and classifier selections. */
export const buildModelConfig = (
  detector: DetectorModelEntry,
  classifier: ClassifierModelEntry,
): ModelConfig => {
  return {
    id: `${detector.id}+${classifier.id}`,
    detectorModel: detector.model,
    classifierModel: classifier.model,
    detectorThreshold: detector.threshold,
    classifierTopK: classifier.topK,
    detectorModelFileName: detector.modelFileName,
    minBoxSize: classifier.minBoxSize,
  };
};

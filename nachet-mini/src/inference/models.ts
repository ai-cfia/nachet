import type { InferenceResult } from "@common/types";

/**
 * Detector flavor. `object-detection` is the classic single-file closed-
 * vocabulary shape (RT-DETR, DETR). `text-promptable-segmentation` is the
 * SAM 3 shape — multi-component, takes a text prompt, open vocabulary.
 */
export type DetectorKind = "object-detection" | "text-promptable-segmentation";

/** Filenames for a multi-file detector's components (e.g. SAM 3's three ONNX files). */
export interface DetectorComponentFiles {
  /** Vision encoder ONNX filename (without `.onnx`) */
  vision: string;
  /** Text encoder ONNX filename (without `.onnx`) */
  text: string;
  /** Decoder ONNX filename (without `.onnx`) */
  decoder: string;
}

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
  /** Detector kind. Defaults to `"object-detection"`. */
  detectorKind?: DetectorKind;
  /** If true, UI shows a text-prompt input and worker expects `prompt` on run-inference. */
  detectorRequiresPrompt?: boolean;
  /** For multi-file detectors: ONNX filenames within `detectorModel`'s HF repo. */
  detectorComponentFiles?: DetectorComponentFiles;
  /** Alternate HF repo for tokenizer/processor when weights and config live separately (e.g. SAM 3). */
  detectorPreprocessorModel?: string;
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
  /** What kind of detector this is. Defaults to `"object-detection"`. */
  kind?: DetectorKind;
  /** True if the UI should show a text-prompt input when this detector is selected. */
  requiresPrompt?: boolean;
  /** For multi-file detectors (e.g. SAM3): which ONNX files make up the model. */
  componentFiles?: DetectorComponentFiles;
  /** Alternate HF repo for tokenizer/processor when weights and config live separately. */
  preprocessorModel?: string;
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
  | {
      type: "run-inference";
      imageSrc: string;
      imageIndex: number;
      /**
       * Text concept prompt for text-promptable detectors (e.g. SAM3). Required
       * when the active detector has `requiresPrompt=true`; ignored otherwise.
       */
      prompt?: string;
    }
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
    id: "detr-resnet-50 0spp",
    model: "Xenova/detr-resnet-50",
    threshold: 0.5,
  },
  {
    // SAM 3 — text-promptable concept segmentation. Takes a free-text
    // concept ("seed", "weed seed", etc.) and detects matching instances.
    // fp32 unfused, 3.3 GB. Needs VRAM headroom (1.72 GB attention buffer
    // per global-attention layer). Faster than MHA-fused below when memory
    // isn't the bottleneck; fall back to MHA-fused on tighter hardware.
    // https://huggingface.co/danilobukvic/sam3-text-onnx
    id: "sam3 fp32",
    model: "danilobukvic/sam3-text-onnx",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
    requiresPrompt: true,
    componentFiles: {
      vision: "vision_encoder",
      text: "text_encoder",
      decoder: "decoder",
    },
  },
  {
    // SAM 3 with fused MultiHeadAttention — memory-constrained fallback.
    // The 32 attention blocks are collapsed into com.microsoft.MultiHeadAttention
    // ops that ORT-Web routes to its FlashAttention-2 kernel (O(N) tiles
    // instead of the unfused variant's 1.72 GB O(N²) score matrices).
    // Slower than unfused on GPUs with headroom; pick this when unfused OOMs.
    // Parity-checked vs unfused (max abs diff 4.3e-4). Fused in custom_mha_fusion.py.
    id: "sam3 fp32 MHA-fused (browser-optimized)",
    model: "danilobukvic/sam3-text-onnx",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
    requiresPrompt: true,
    componentFiles: {
      vision: "vision_encoder_mhafused", // ← the new fused vision encoder
      text: "text_encoder", // unchanged (no attention to fuse there)
      decoder: "decoder", // unchanged
    },
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
    // Multi-component / text-promptable detector fields. Undefined for the
    // standard single-file object-detection detectors.
    detectorKind: detector.kind,
    detectorRequiresPrompt: detector.requiresPrompt,
    detectorComponentFiles: detector.componentFiles,
    detectorPreprocessorModel: detector.preprocessorModel,
  };
};

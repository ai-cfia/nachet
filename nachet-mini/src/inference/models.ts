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
  /**
   * Detector kind. Defaults to `"object-detection"`. The
   * `text-promptable-segmentation` kind is what drives the prompt UI and the
   * worker's `prompt` expectation — there's no separate boolean for it.
   *
   * Same value as `DetectorModelEntry.kind`; `buildModelConfig` copies it here
   * and prefixes it `detector` because `ModelConfig` flattens the selected
   * detector and classifier entries into one object sent to the worker.
   */
  detectorKind?: DetectorKind;
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
  /**
   * What kind of detector this is. Defaults to `"object-detection"`.
   * `text-promptable-segmentation` (e.g. SAM3) is what makes the UI show a
   * text-prompt input — no separate `requiresPrompt` flag needed.
   *
   * This is the registry-entry field; `buildModelConfig` copies it onto the
   * flattened `ModelConfig` as `detectorKind`.
   */
  kind?: DetectorKind;
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
       * when the active detector's kind is `text-promptable-segmentation`;
       * `null` (or omitted) for closed-vocabulary detectors that ignore it.
       */
      prompt?: string | null;
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
  | {
      // Class Activation Maps for one classified box: one heatmap per top-K
      // class, showing which regions drive that species' score. Streamed
      // separately so boxes render immediately and overlays arrive per seed.
      type: "cam-result";
      imageIndex: number;
      modelConfigId: string;
      boxId: string;
      /** spatial grid side (e.g. 12 → 12×12 = 144 tokens). */
      grid: number;
      /** Per top-K class: index, label, score, and its `grid*grid` heatmap [0,1]. */
      classes: {
        classIndex: number;
        label: string;
        score: number;
        heatmap: number[];
      }[];
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
  {
    // SAM 3 — text-promptable concept segmentation. Takes a free-text
    // concept ("seed", "weed seed", etc.) and detects matching instances.
    // fp32 unfused, 3.3 GB. Needs VRAM headroom (1.72 GB attention buffer
    // per global-attention layer). Faster than MHA-fused below when memory
    // isn't the bottleneck; fall back to MHA-fused on tighter hardware.
    // https://huggingface.co/cfia-ai-lab/sam3-text-onnx
    id: "sam3 fp32",
    model: "cfia-ai-lab/sam3-text-onnx",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
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
    model: "cfia-ai-lab/sam3-text-onnx",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
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
    id: "swin-L 101spp",
    model: "cfia-ai-lab/swin-large-patch4-window12-384-in22k-101spp-ft",
    topK: 5,
    minBoxSize: 384,
  },
  {
    id: "swin-L 101spp CAM",
    // Same 101spp model, but this repo's onnx/model.onnx is the patched FP16
    // export that also outputs `swin_layernorm`. Selecting this entry enables
    // the per-species Class Activation Maps in the results panel; the plain
    // "swin-L 101spp" entry above has no such output, so that UI stays hidden.
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
    // Multi-component / text-promptable detector fields. Undefined for the
    // standard single-file object-detection detectors.
    detectorKind: detector.kind,
    detectorComponentFiles: detector.componentFiles,
    detectorPreprocessorModel: detector.preprocessorModel,
  };
};

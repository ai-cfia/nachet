import type { InferenceResult } from "@common/types";

/**
 * Detector "kind" — what flavor of detector this is.
 *
 * - `"object-detection"`: standard single-pass detector (RT-DETR, DETR). Image
 *   in → boxes out. Closed vocabulary (only knows the classes it was trained on).
 * - `"text-promptable-segmentation"`: multi-component detector that takes both
 *   an image and a free-text concept prompt (e.g. SAM3). Outputs instance masks
 *   and boxes for objects matching the prompt. Open vocabulary.
 */
export type DetectorKind = "object-detection" | "text-promptable-segmentation";

/**
 * Component filenames for a multi-file detector. Used by
 * text-promptable-segmentation detectors that ship multiple ONNX files
 * (e.g. SAM3 has vision_encoder, text_encoder, decoder).
 */
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
   * What kind of detector this is. Defaults to `"object-detection"` (the
   * original single-file pattern). Set to `"text-promptable-segmentation"`
   * for SAM3-style detectors that take an additional text prompt.
   */
  detectorKind?: DetectorKind;
  /**
   * If true, the worker expects a `prompt` field on `run-inference` messages.
   * The UI should render a text input when a model with this flag is selected.
   */
  detectorRequiresPrompt?: boolean;
  /**
   * For multi-file detectors: filenames of the component ONNX files within
   * `detectorModel`'s HF repo. If set, the worker loads these instead of the
   * single `detectorModelFileName`.
   */
  detectorComponentFiles?: DetectorComponentFiles;
  /**
   * Some detectors ship their ONNX weights in a separate HF repo from the
   * tokenizer/processor config (e.g. our SAM3 ONNX is at
   * `danilobukvic/sam3-text-onnx` but the processor lives at `facebook/sam3`).
   * If set, the worker loads tokenizer/processor from this repo instead of
   * `detectorModel`.
   */
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
  /**
   * Optional alternate HF repo for tokenizer/preprocessor. Use this when the
   * ONNX weights live in one repo but the processor config lives in another
   * (e.g. SAM3: weights at `danilobukvic/sam3-text-onnx`, processor at
   * `facebook/sam3`).
   */
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
    // SAM3 — Meta's text-promptable concept segmentation, int8-quantized for
    // browser deployment. Unlike the closed-vocabulary detectors above, this
    // takes a free-text prompt ("seed", "weed seed", "insect", etc.).
    // 839 MB total download (3 ONNX files: vision + text + decoder).
    // See: https://huggingface.co/danilobukvic/sam3-text-onnx
    id: "sam3 int8 (text-promptable)",
    model: "danilobukvic/sam3-text-onnx",
    preprocessorModel: "facebook/sam3",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
    requiresPrompt: true,
    componentFiles: {
      vision: "vision_encoder_int8",
      text: "text_encoder_int8",
      decoder: "decoder_int8",
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

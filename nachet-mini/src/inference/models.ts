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
    id: "detr-resnet-50 0spp",
    model: "Xenova/detr-resnet-50",
    threshold: 0.5,
  },
  {
    // SAM3 — Meta's text-promptable concept segmentation, int4-quantized for
    // browser deployment. Unlike the closed-vocabulary detectors above, this
    // takes a free-text prompt ("seed", "weed seed", "insect", etc.).
    //
    // Why int4, not int8: dynamic int8 quantization inserts `ConvInteger`
    // nodes around the FPN Conv2d layers in the vision encoder. The web
    // runtime (onnxruntime-web wasm + webgpu) doesn't ship implementations
    // of ConvInteger — the model fails to load with "Could not find an
    // implementation for ConvInteger(10)" once parsed.
    //
    // The int4 variant uses MatMulNBitsQuantizer, which only quantizes
    // MatMul ops and leaves Conv ops at fp32. Larger weights, but every
    // op has a web implementation.
    //
    // 654 MB total download (3 ONNX files: vision + text + decoder).
    // See: https://huggingface.co/danilobukvic/sam3-text-onnx
    id: "sam3 int4 (text-promptable)",
    model: "danilobukvic/sam3-text-onnx",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
    requiresPrompt: true,
    componentFiles: {
      vision: "vision_encoder_int4",
      text: "text_encoder_int4",
      decoder: "decoder_int4",
    },
  },
  {
    // fp32 reference variant — same model, no quantization. 3.3 GB download.
    // Likely too memory-heavy for browser execution on consumer hardware
    // (~4 GB VRAM/RAM), but kept as an experimental option for WebGPU EP
    // testing: the int4 variant trips the WebGPU EP's graph capture on
    // MatMulNBits ops, but fp32 only has standard ops so it should at
    // least *load* on WebGPU even if it OOMs during the forward pass.
    id: "sam3 fp32 (text-promptable, experimental)",
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
    // fp32 with FUSED MultiHeadAttention — this is the breakthrough variant.
    //
    // The vision encoder's 32 attention blocks were collapsed from
    // {QK MatMul → Softmax → V MatMul} into single com.microsoft.MultiHeadAttention
    // contrib ops (with Transpose+Reshape around them for layout conversion).
    // ORT-Web's WebGPU EP routes MultiHeadAttention to its FlashAttention-2
    // kernel — O(N) memory tiles instead of materializing O(N²) score matrices.
    // The fp32 variant materialized a 1.72 GB attention buffer per global
    // attention layer; this one should use ~tens of MB.
    //
    // Parity-validated against the unfused fp32 model (max abs diff 4.3e-4 on
    // FPN outputs — fp32 rounding noise). CPU inference 3.9x faster even
    // without FlashAttention. Custom fusion built in fuse_vision_encoder.py
    // since ORT's TryFuseMobileClipMHA matcher couldn't handle SAM 3's
    // separate Q/K/V projections + RoPE pattern.
    id: "sam3 fp32 MHA-fused (browser-optimized)",
    model: "danilobukvic/sam3-text-onnx",
    threshold: 0.5,
    kind: "text-promptable-segmentation",
    requiresPrompt: true,
    componentFiles: {
      vision: "vision_encoder_mhafused",  // ← the new fused vision encoder
      text: "text_encoder",                 // unchanged (no attention to fuse there)
      decoder: "decoder",                   // unchanged
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

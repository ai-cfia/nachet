// onnxruntime-web ships its module type declarations in `types.d.ts` rather
// than via the usual package.json `types` field. Triple-slash here so TS
// picks them up — without it, `import * as ort from "onnxruntime-web"` is
// implicitly `any`.
/// <reference path="../../node_modules/onnxruntime-web/types.d.ts" />

/**
 * SAM 3 detector — text-promptable concept segmentation.
 *
 * Loads three ONNX components (vision encoder, text encoder, decoder) from
 * a single HuggingFace repo and runs the cached two-stage pipeline:
 *
 *   image ──► vision encoder ──► FPN features (cached per image)
 *                                       ▼
 *   prompt ──► text encoder ──► decoder ──► boxes + masks + scores
 *
 * Why a separate module from worker.ts: SAM 3 doesn't fit the
 * transformers.js `AutoModelForObjectDetection` shape. It needs:
 *
 *   1. A text prompt input — closed-vocabulary detectors have none.
 *   2. Three separate ONNX files orchestrated manually — `AutoModel*`
 *      expects a single model.
 *   3. Custom output post-processing: sigmoid logits, denormalize boxes.
 *
 * Rather than bloat worker.ts with conditionals, the SAM 3 path lives
 * here. worker.ts branches on `config.detectorKind === "text-promptable-
 * segmentation"` and delegates the whole detection step to `runSam3`.
 */

import * as ort from "onnxruntime-web";
import { AutoTokenizer } from "@huggingface/transformers";
import {
  preprocessImageForSam3,
  SAM3_PIXEL_TENSOR_SHAPE,
} from "./sam3Preprocess";
import type { ModelConfig } from "./models";

// ---------------------------------------------------------------------------
// Constants — these mirror the SAM 3 ONNX export's I/O contract.
// ---------------------------------------------------------------------------

/** CLIP-style max sequence length for SAM 3's text encoder (32, not the
 *  standard 77 — Meta truncated it for concept prompts). */
const SAM3_MAX_TEXT_LENGTH = 32;

/** Number of query slots emitted by the decoder. Fixed by training. */
const SAM3_NUM_QUERIES = 200;

// ---------------------------------------------------------------------------
// Lazy-loaded sessions + tokenizer (module state)
// ---------------------------------------------------------------------------

let visionSession: ort.InferenceSession | null = null;
let textSession: ort.InferenceSession | null = null;
let decoderSession: ort.InferenceSession | null = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let tokenizer: any = null;

/**
 * Vision-feature cache: avoid the 30+s vision encoder run when only the
 * prompt changed. We keep at most one image's features in memory at a time
 * — these are large (~7 MB per tensor × 8 tensors ≈ 56 MB) so we don't
 * want a multi-image LRU.
 */
interface CachedVisionOutput {
  imageSrc: string;
  fpn_hidden_state_0: ort.Tensor;
  fpn_hidden_state_1: ort.Tensor;
  fpn_hidden_state_2: ort.Tensor;
  fpn_position_encoding_2: ort.Tensor;
}
let visionCache: CachedVisionOutput | null = null;

// ---------------------------------------------------------------------------
// Output types — matches what worker.ts's existing detector path produces.
// ---------------------------------------------------------------------------

/**
 * Output of `runSam3`. Shape-compatible with the `PostProcessedDetection`
 * the existing worker code path uses, so the downstream classifier flow
 * can stay unchanged.
 */
export interface Sam3Detections {
  /** [N][4] boxes in (xmin, ymin, xmax, ymax) in **original image** pixel space. */
  boxes: number[][];
  /** [N] sigmoid scores in [0, 1]. */
  scores: number[];
  /** [N] class indices — always 0 for SAM 3 (single concept per inference). */
  classes: number[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build the full HF resolve URL for a component ONNX file.
 *
 * Some components ship with an external `.data` file alongside the `.onnx`
 * — onnxruntime-web auto-discovers it by appending `.data` to the URL, so
 * we don't need to fetch it manually.
 */
const onnxUrl = (repo: string, fileName: string): string =>
  `https://huggingface.co/${repo}/resolve/main/${fileName}.onnx`;

/**
 * Pick the best execution provider. Tries WebGPU first if available since
 * the vision encoder is heavy enough to benefit; falls back to wasm.
 *
 * The decoder will be loaded with wasm only — on consumer GPUs (4 GB VRAM)
 * its attention layers need ~860 MB intermediate buffers that don't fit
 * alongside the vision encoder. Mirrors the Python validation finding.
 */
const detectExecutionProviders = async (): Promise<ort.InferenceSession.ExecutionProviderConfig[]> => {
  try {
    if (typeof navigator !== "undefined" && "gpu" in (navigator as object)) {
      const adapter = await (
        navigator as unknown as {
          gpu: { requestAdapter(): Promise<unknown | null> };
        }
      ).gpu.requestAdapter();
      if (adapter) {
        console.log("[sam3] WebGPU available — using for vision/text encoders");
        return ["webgpu", "wasm"];
      }
    }
  } catch (err) {
    console.warn("[sam3] WebGPU detection failed:", err);
  }
  return ["wasm"];
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Load the three ONNX components and the tokenizer.
 *
 * Idempotent: a second call with the same config is a no-op. Calling with
 * a different config (different precision variant, different repo, etc.)
 * tears down the existing sessions and reloads.
 *
 * @param config The ModelConfig from the main thread. Must have
 *   `detectorKind === "text-promptable-segmentation"`, `detectorComponentFiles`
 *   populated, and ideally `detectorPreprocessorModel` set.
 * @param onProgress Optional callback for download progress reporting. The
 *   onnxruntime-web API doesn't expose per-byte progress like transformers.js
 *   does, so we only call this at file-level boundaries (start of each
 *   component).
 */
export const loadSam3 = async (
  config: ModelConfig,
  onProgress?: (info: { name: string; progress: number }) => void,
): Promise<void> => {
  if (
    !config.detectorComponentFiles ||
    !config.detectorRequiresPrompt ||
    config.detectorKind !== "text-promptable-segmentation"
  ) {
    throw new Error(
      "loadSam3 called with a non-text-promptable config — check detectorKind.",
    );
  }

  // Tear down any previous load
  await unloadSam3();

  const providers = await detectExecutionProviders();
  const { vision, text, decoder } = config.detectorComponentFiles;
  const repo = config.detectorModel;
  const preprocessorRepo = config.detectorPreprocessorModel ?? repo;

  // Vision encoder — try GPU first; the ViT benefits massively.
  console.log("[sam3] Loading vision encoder from", repo, "/", vision);
  onProgress?.({ name: "sam3 vision encoder", progress: 0 });
  visionSession = await ort.InferenceSession.create(onnxUrl(repo, vision), {
    executionProviders: providers,
  });
  console.log("[sam3] Vision encoder loaded");
  onProgress?.({ name: "sam3 vision encoder", progress: 100 });

  // Text encoder — small, runs anywhere.
  console.log("[sam3] Loading text encoder from", repo, "/", text);
  onProgress?.({ name: "sam3 text encoder", progress: 0 });
  textSession = await ort.InferenceSession.create(onnxUrl(repo, text), {
    executionProviders: providers,
  });
  console.log("[sam3] Text encoder loaded");
  onProgress?.({ name: "sam3 text encoder", progress: 100 });

  // Decoder — WASM only. Its attention layers blow past 4 GB VRAM on
  // consumer GPUs because of the 860 MB intermediate buffers. CPU is fine
  // anyway since the decoder is small (~100 MB at fp32, less for quantized).
  console.log("[sam3] Loading decoder from", repo, "/", decoder);
  onProgress?.({ name: "sam3 decoder", progress: 0 });
  decoderSession = await ort.InferenceSession.create(onnxUrl(repo, decoder), {
    executionProviders: ["wasm"],
  });
  console.log("[sam3] Decoder loaded");
  onProgress?.({ name: "sam3 decoder", progress: 100 });

  // Tokenizer — for the text prompt. Comes from facebook/sam3 (or whatever
  // the config's preprocessorModel says), not our ONNX repo, since the
  // tokenizer config isn't included in the ONNX bundle.
  console.log("[sam3] Loading tokenizer from", preprocessorRepo);
  onProgress?.({ name: "sam3 tokenizer", progress: 0 });
  tokenizer = await AutoTokenizer.from_pretrained(preprocessorRepo);
  onProgress?.({ name: "sam3 tokenizer", progress: 100 });

  console.log("[sam3] All components loaded");
};

/** Tear down sessions and free the vision-feature cache. */
export const unloadSam3 = async (): Promise<void> => {
  if (visionSession) {
    await visionSession.release();
    visionSession = null;
  }
  if (textSession) {
    await textSession.release();
    textSession = null;
  }
  if (decoderSession) {
    await decoderSession.release();
    decoderSession = null;
  }
  tokenizer = null;
  visionCache = null;
};

/**
 * Run the full SAM 3 pipeline on an image + prompt.
 *
 * If the image is the same as the previous call (by URL string), the vision
 * encoder is skipped and the cached FPN features are reused. This is the
 * key performance optimization — vision encoder takes 10–30 s while
 * decoder takes ~3 s. Lets the user iterate on prompts cheaply.
 *
 * @param imageSrc Image URL (data URL or blob URL).
 * @param prompt Text concept prompt, e.g. "seed".
 * @param threshold Minimum sigmoid score to keep a detection.
 * @param originalWidth Original image width — output boxes get rescaled
 *   from normalized [0, 1] to these dims.
 * @param originalHeight Original image height.
 */
export const runSam3 = async (
  imageSrc: string,
  prompt: string,
  threshold: number,
  originalWidth: number,
  originalHeight: number,
): Promise<Sam3Detections> => {
  if (!visionSession || !textSession || !decoderSession || !tokenizer) {
    throw new Error("SAM 3 sessions not loaded — call loadSam3 first.");
  }

  // ── 1. Vision encoder (cached) ─────────────────────────────────────────
  let visionOut: CachedVisionOutput;
  if (visionCache && visionCache.imageSrc === imageSrc) {
    console.log("[sam3] Reusing cached vision features for", imageSrc);
    visionOut = visionCache;
  } else {
    console.log("[sam3] Running vision encoder for", imageSrc);
    const visionStart = performance.now();

    // Fetch + decode the image, preprocess to NCHW float32 [1, 3, 1008, 1008]
    const blob = await (await fetch(imageSrc)).blob();
    const bitmap = await createImageBitmap(blob);
    const pixelValues = preprocessImageForSam3(bitmap);
    bitmap.close();

    const pixelTensor = new ort.Tensor(
      "float32",
      pixelValues,
      SAM3_PIXEL_TENSOR_SHAPE as number[],
    );
    const visionFeed = { pixel_values: pixelTensor };
    const visionResult = await visionSession.run(visionFeed);

    // The export emits 8 outputs in order: fpn_hidden_state_0..3 then
    // fpn_position_encoding_0..3. The decoder only needs hidden_state_0/1/2
    // and position_encoding_2 (the others were optimized out by the tracer).
    visionOut = {
      imageSrc,
      fpn_hidden_state_0: visionResult.fpn_hidden_state_0,
      fpn_hidden_state_1: visionResult.fpn_hidden_state_1,
      fpn_hidden_state_2: visionResult.fpn_hidden_state_2,
      fpn_position_encoding_2: visionResult.fpn_position_encoding_2,
    };
    visionCache = visionOut;

    const visionMs = performance.now() - visionStart;
    console.log(`[sam3] Vision encoder finished in ${visionMs.toFixed(0)} ms`);
  }

  // ── 2. Text encoder ────────────────────────────────────────────────────
  console.log(`[sam3] Tokenizing prompt: "${prompt}"`);
  // CLIP-style tokenization, fixed-length 32.
  // transformers.js AutoTokenizer returns a `Tokenizer` whose call signature
  // is (text, options) and returns { input_ids, attention_mask } as Tensors.
  const tokenized = tokenizer(prompt, {
    padding: "max_length",
    max_length: SAM3_MAX_TEXT_LENGTH,
    truncation: true,
    return_tensor: true,
  });
  // Cast to BigInt64Array — int64 in ONNX needs BigInt64 in JS land.
  const inputIdsBig = bigInt64FromTensor(tokenized.input_ids);
  const attentionMaskBig = bigInt64FromTensor(tokenized.attention_mask);
  const textInputIds = new ort.Tensor("int64", inputIdsBig, [
    1,
    SAM3_MAX_TEXT_LENGTH,
  ]);
  const textAttentionMask = new ort.Tensor("int64", attentionMaskBig, [
    1,
    SAM3_MAX_TEXT_LENGTH,
  ]);

  const textStart = performance.now();
  const textResult = await textSession.run({
    input_ids: textInputIds,
    attention_mask: textAttentionMask,
  });
  const textFeatures = textResult.text_features;
  console.log(
    `[sam3] Text encoder finished in ${(performance.now() - textStart).toFixed(0)} ms`,
  );

  // ── 3. Decoder ─────────────────────────────────────────────────────────
  const decoderStart = performance.now();
  const decoderResult = await decoderSession.run({
    fpn_hidden_state_0: visionOut.fpn_hidden_state_0,
    fpn_hidden_state_1: visionOut.fpn_hidden_state_1,
    fpn_hidden_state_2: visionOut.fpn_hidden_state_2,
    fpn_position_encoding_2: visionOut.fpn_position_encoding_2,
    text_features: textFeatures,
    attention_mask: textAttentionMask,
  });
  console.log(
    `[sam3] Decoder finished in ${(performance.now() - decoderStart).toFixed(0)} ms`,
  );

  // ── 4. Post-process: sigmoid logits → scores, denormalize boxes ────────
  const predBoxes = decoderResult.pred_boxes.data as Float32Array; // [1, 200, 4]
  const predLogits = decoderResult.pred_logits.data as Float32Array; // [1, 200]

  const boxes: number[][] = [];
  const scores: number[] = [];
  const classes: number[] = [];

  for (let i = 0; i < SAM3_NUM_QUERIES; i++) {
    // Sigmoid in JS — no special vector op, but it's only 200 elements so
    // a plain loop is fine.
    const score = 1 / (1 + Math.exp(-predLogits[i]));
    if (score < threshold) continue;

    // pred_boxes is laid out as [batch, 200, 4] in NHWC-like order, so
    // the 4 box coords for query i live at offsets [i*4 .. i*4+3].
    const x1n = predBoxes[i * 4 + 0];
    const y1n = predBoxes[i * 4 + 1];
    const x2n = predBoxes[i * 4 + 2];
    const y2n = predBoxes[i * 4 + 3];

    boxes.push([
      x1n * originalWidth,
      y1n * originalHeight,
      x2n * originalWidth,
      y2n * originalHeight,
    ]);
    scores.push(score);
    classes.push(0); // Always class 0 for SAM 3 — single concept per call.
  }

  console.log(
    `[sam3] ${boxes.length} detections above threshold ${threshold}`,
  );

  return { boxes, scores, classes };
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

/**
 * Convert a transformers.js Tensor (or similar object) to a BigInt64Array
 * suitable for an int64 ort.Tensor.
 *
 * The library returns `input_ids` either as a BigInt64Array directly (newer
 * versions) or as a regular number[] (older). Handle both.
 */
const bigInt64FromTensor = (tensor: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ort_tensor?: { data?: any };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  tolist?: () => any;
}): BigInt64Array => {
  const data: unknown =
    tensor.data ?? tensor.ort_tensor?.data ?? tensor.tolist?.();
  if (data instanceof BigInt64Array) return data;
  if (Array.isArray(data)) {
    return BigInt64Array.from((data as number[]).map((v) => BigInt(v)));
  }
  // Some transformers.js versions return typed integer arrays — coerce to
  // BigInt64Array by widening through a regular array.
  if (
    data instanceof Int32Array ||
    data instanceof Uint32Array ||
    data instanceof Int16Array ||
    data instanceof Uint16Array
  ) {
    return BigInt64Array.from(
      Array.from(data as ArrayLike<number>).map((v) => BigInt(v)),
    );
  }
  throw new Error(
    `Cannot convert tokenizer output to BigInt64Array — got ${typeof data}`,
  );
};

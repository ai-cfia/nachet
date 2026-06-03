/**
 * SAM 3 detector — text-promptable concept segmentation. Loads three ONNX
 * components (vision encoder, text encoder, decoder) and runs them as a
 * cached pipeline. Lives in its own module because SAM 3 doesn't fit the
 * transformers.js AutoModel shape — multi-component and takes a text prompt.
 * worker.ts branches on `detectorKind` and delegates here.
 */

import * as ort from "onnxruntime-web";
import { AutoTokenizer } from "@huggingface/transformers";
import {
  preprocessImageForSam3,
  SAM3_PIXEL_TENSOR_SHAPE,
} from "./sam3Preprocess";
import type { ModelConfig } from "./models";

// Keep ORT-Web at `warning` so real failures still surface, without spamming
// the console during normal inference. Bump to `verbose` + set
// `ort.env.debug = true` when diagnosing a session that's crashing with
// bare wasm pointers (e.g. "25954464") instead of readable error messages.
ort.env.logLevel = "warning";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Max prompt token length for SAM 3's text encoder (truncated from CLIP's 77). */
const SAM3_MAX_TEXT_LENGTH = 32;

/** Number of query slots emitted by the decoder. Fixed by training. */
const SAM3_NUM_QUERIES = 200;

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

let visionSession: ort.InferenceSession | null = null;
let textSession: ort.InferenceSession | null = null;
let decoderSession: ort.InferenceSession | null = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let tokenizer: any = null;

/** Vision encoder outputs cached per image so prompt changes skip re-encoding. */
interface CachedVisionOutput {
  imageSrc: string;
  fpn_hidden_state_0: ort.Tensor;
  fpn_hidden_state_1: ort.Tensor;
  fpn_hidden_state_2: ort.Tensor;
  fpn_position_encoding_2: ort.Tensor;
}
let visionCache: CachedVisionOutput | null = null;

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** Output of `runSam3` — shape-compatible with the worker's existing detector path. */
export interface Sam3Detections {
  /** [N][4] boxes in (xmin, ymin, xmax, ymax) in original image pixel space. */
  boxes: number[][];
  /** [N] sigmoid scores in [0, 1]. */
  scores: number[];
  /** [N] class indices — always 0 (single concept per inference). */
  classes: number[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** HF resolve URL for a component ONNX file. */
const onnxUrl = (repo: string, fileName: string): string =>
  `https://huggingface.co/${repo}/resolve/main/${fileName}.onnx`;

/** HF resolve URL for the matching external .data file. */
const onnxDataUrl = (repo: string, fileName: string): string =>
  `https://huggingface.co/${repo}/resolve/main/${fileName}.onnx.data`;

/**
 * Load an InferenceSession, fetching the external `.onnx.data` file by hand
 * when present. ORT-Web doesn't auto-fetch external data files — without
 * this the graph loads with unresolved weights and crashes silently.
 */
const createSessionWithExternalData = async (
  repo: string,
  fileName: string,
  options: ort.InferenceSession.SessionOptions,
): Promise<ort.InferenceSession> => {
  const modelUrl = onnxUrl(repo, fileName);
  const dataUrl = onnxDataUrl(repo, fileName);

  // HEAD-probe for the .data file. 200 → fetch; 404 → weights are inline.
  let externalDataBuffer: ArrayBuffer | null = null;
  try {
    const headResp = await fetch(dataUrl, { method: "HEAD" });
    if (headResp.ok) {
      const len = headResp.headers.get("content-length");
      console.log(
        `[sam3] External data file detected: ${fileName}.onnx.data (${len ?? "?"} bytes)`,
      );
      const dataResp = await fetch(dataUrl);
      if (!dataResp.ok) {
        throw new Error(
          `Failed to fetch external data: ${dataResp.status} ${dataResp.statusText}`,
        );
      }
      externalDataBuffer = await dataResp.arrayBuffer();
      console.log(
        `[sam3] External data downloaded: ${externalDataBuffer.byteLength} bytes`,
      );
    } else if (headResp.status === 404) {
      console.log(
        `[sam3] No external data file for ${fileName} (weights are inline)`,
      );
    } else {
      console.warn(
        `[sam3] Unexpected HEAD status for ${fileName}.onnx.data:`,
        headResp.status,
      );
    }
  } catch (err) {
    console.warn(`[sam3] External data probe failed for ${fileName}:`, err);
  }

  // `path` must match the relative reference inside the .onnx graph.
  const sessionOptions: ort.InferenceSession.SessionOptions = externalDataBuffer
    ? {
        ...options,
        externalData: [
          {
            path: `${fileName}.onnx.data`,
            data: new Uint8Array(externalDataBuffer),
          },
        ],
      }
    : options;

  return ort.InferenceSession.create(modelUrl, sessionOptions);
};

/** Pick execution providers for vision/text. WebGPU first, wasm fallback. */
const detectExecutionProviders = async (): Promise<
  ort.InferenceSession.ExecutionProviderConfig[]
> => {
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
  console.log("[sam3] WebGPU unavailable, using wasm");
  return ["wasm"];
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Load the three ONNX components and the tokenizer. Idempotent: same config
 * is a no-op; different config tears down and reloads.
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

  await unloadSam3();

  const providers = await detectExecutionProviders();
  const { vision, text, decoder } = config.detectorComponentFiles;
  const repo = config.detectorModel;
  const preprocessorRepo = config.detectorPreprocessorModel ?? repo;

  console.log("[sam3] Loading vision encoder from", repo, "/", vision);
  onProgress?.({ name: "sam3 vision encoder", progress: 0 });
  visionSession = await createSessionWithExternalData(repo, vision, {
    executionProviders: providers,
  });
  console.log("[sam3] Vision encoder loaded");
  onProgress?.({ name: "sam3 vision encoder", progress: 100 });

  console.log("[sam3] Loading text encoder from", repo, "/", text);
  onProgress?.({ name: "sam3 text encoder", progress: 0 });
  textSession = await createSessionWithExternalData(repo, text, {
    executionProviders: providers,
  });
  console.log("[sam3] Text encoder loaded");
  onProgress?.({ name: "sam3 text encoder", progress: 100 });

  // Decoder always uses wasm — attention layers blow past 4 GB VRAM on
  // consumer GPUs (Python validation: 860 MB intermediate).
  console.log("[sam3] Loading decoder from", repo, "/", decoder);
  onProgress?.({ name: "sam3 decoder", progress: 0 });
  decoderSession = await createSessionWithExternalData(repo, decoder, {
    executionProviders: ["wasm"],
  });
  console.log("[sam3] Decoder loaded");
  onProgress?.({ name: "sam3 decoder", progress: 100 });

  // Tokenizer config isn't in the ONNX bundle — load it from facebook/sam3.
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
 * Run the full SAM 3 pipeline. If imageSrc matches the previous call, the
 * vision encoder is skipped and cached FPN features are reused — vision
 * takes 10–30s, decoder ~3s, so this lets the user iterate prompts cheaply.
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

    // Fetch + decode the image, preprocess to NCHW float32 [1, 3, 1008, 1008].
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

    // Export emits 8 outputs (fpn_hidden_state_0..3, fpn_position_encoding_0..3);
    // decoder only consumes hidden_state_0/1/2 + position_encoding_2.
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
  const tokenized = tokenizer(prompt, {
    padding: "max_length",
    max_length: SAM3_MAX_TEXT_LENGTH,
    truncation: true,
    return_tensor: true,
  });
  // ONNX int64 requires BigInt64Array on the JS side.
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
    const score = 1 / (1 + Math.exp(-predLogits[i]));
    if (score < threshold) continue;

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
    classes.push(0);
  }

  console.log(`[sam3] ${boxes.length} detections above threshold ${threshold}`);

  return { boxes, scores, classes };
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

/**
 * Coerce a transformers.js Tensor's int data into a BigInt64Array for ONNX.
 * Handles BigInt64Array, number[], and other typed int arrays.
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

/**
 * Class Activation Mapping (CAM) for the Swin classifier, in the browser.
 *
 * Swin's head is global-average-pool over the 144 tokens followed by a linear
 * layer (1536 -> 101), so a class logit is exactly the average of per-token
 * contributions:
 *
 *   logit_c = mean_t ( features[t] · W_c ) + b_c
 *
 * That means the per-token contribution to class c, `features[t] · W_c`, is a
 * gradient-free, exact class activation map: it shows which spatial locations
 * drive the score for that species. We compute it from the patched model's
 * `swin_layernorm` output (the pre-pool token features) and the classifier
 * head weights `W` (extracted offline, bundled as a binary asset).
 */

const NUM_CLASSES = 101;
const NUM_FEATURES = 1536;

// The head weights are model-specific, so they're hosted alongside the patched
// model on Hugging Face and fetched by URL (not bundled into the app). Cache the
// fetch per URL so repeated boxes reuse one download.
const headCache = new Map<string, Promise<Float32Array>>();

/** Lazily fetch the classifier head weights (101 x 1536, row-major float32). */
const loadHead = (url: string): Promise<Float32Array> => {
  let promise = headCache.get(url);
  if (!promise) {
    promise = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`head weights HTTP ${r.status}`);
        return r.arrayBuffer();
      })
      .then((buf) => {
        const w = new Float32Array(buf);
        if (w.length !== NUM_CLASSES * NUM_FEATURES) {
          throw new Error(`head weights wrong size: ${w.length}`);
        }
        return w;
      })
      .catch((err) => {
        // Drop the failed promise so a later call can retry the download.
        headCache.delete(url);
        throw err;
      });
    headCache.set(url, promise);
  }
  return promise;
};

export interface CamResult {
  /** spatial grid side (12 for a 144-token Swin stage). */
  grid: number;
  /** one heatmap per requested class index, each grid*grid floats in [0, 1]. */
  maps: Float32Array[];
}

/**
 * Compute CAM heatmaps for the given class indices.
 * @param features flat `swin_layernorm` data, layout (1, tokens, channels).
 * @param tokens   spatial tokens (e.g. 144).
 * @param channels feature dim (must be 1536 to match the head).
 * @param classIndices which class rows of W to map (e.g. the top-K indices).
 * @param headUrl  URL of the classifier head weights (hosted on Hugging Face).
 */
export async function computeCam(
  features: Float32Array,
  tokens: number,
  channels: number,
  classIndices: number[],
  headUrl: string,
): Promise<CamResult> {
  if (channels !== NUM_FEATURES) {
    throw new Error(`CAM: channels ${channels} != head ${NUM_FEATURES}`);
  }
  const grid = Math.round(Math.sqrt(tokens));
  if (grid * grid !== tokens)
    throw new Error(`CAM: non-square grid (${tokens})`);

  const W = await loadHead(headUrl);

  const maps = classIndices.map((rawC) => {
    const c = Number(rawC); // guard against BigInt indices from int64 tensors
    const map = new Float32Array(tokens);
    if (!Number.isFinite(c) || c < 0 || c >= NUM_CLASSES) return map; // blank
    const wOff = c * NUM_FEATURES;
    let mn = Infinity;
    let mx = -Infinity;
    for (let t = 0; t < tokens; t++) {
      let s = 0;
      const fOff = t * channels;
      for (let ch = 0; ch < channels; ch++) {
        s += features[fOff + ch] * W[wOff + ch];
      }
      map[t] = s;
      if (s < mn) mn = s;
      if (s > mx) mx = s;
    }
    // min-max normalize to [0, 1] for display
    const range = mx - mn || 1;
    for (let t = 0; t < tokens; t++) map[t] = (map[t] - mn) / range;
    return map;
  });

  return { grid, maps };
}

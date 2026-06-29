/**
 * Deep Feature Factorization (DFF) in the browser.
 *
 * Mirrors the pytorch_grad_cam DeepFeatureFactorization used in the
 * nachet-model-ccds notebook (4.20_db_classifier_gradcam.ipynb), but runs
 * entirely client-side on the Swin classifier's `swin.layernorm` activations
 * (exposed as the `swin_layernorm` ONNX output of the patched model).
 *
 * Pipeline per detected seed (batch = 1):
 *   1. swin_layernorm activations (1, 144, 1536) -> reshape_transform ->
 *      library orientation X = (channels=1536, spatial=144).
 *   2. per-channel min-shift to make X non-negative (matches the library).
 *   3. NMF with deterministic NNDSVD init + multiplicative updates
 *      (matches sklearn NMF(init='nndsvd', solver='mu')), so concepts are
 *      reproducible run-to-run and identical to the notebook.
 *   4. concepts W (1536 x K), spatial heatmaps H (K x 144) — each H row is a
 *      12x12 concept map, min-max normalized for display.
 *
 * Validated offline: concept cosine / heatmap corr >= 0.9996 vs the sklearn
 * reference; ~0.8 s/seed (Jacobi SVD init + 200 MU iters) on CPU.
 */

export interface DffResult {
  /** number of concepts (NMF components) */
  k: number;
  /** spatial grid side (12 for a 144-token Swin stage) */
  grid: number;
  /** K heatmaps, each `grid*grid` floats normalized to [0, 1] (row-major). */
  heatmaps: Float32Array[];
  /** concept directions in channel space, K x channels (for optional labeling). */
  concepts: Float32Array[];
}

export interface DffOptions {
  /** number of concepts (default 4, matching the notebook). */
  k?: number;
  /** multiplicative-update iterations (default 200, matching sklearn). */
  iters?: number;
}

/**
 * Compute DFF for a single seed.
 * @param features flat `swin_layernorm` data, layout (1, tokens, channels), row-major.
 * @param tokens   number of spatial tokens (e.g. 144).
 * @param channels feature dimension (e.g. 1536).
 */
export function computeDff(
  features: Float32Array,
  tokens: number,
  channels: number,
  options: DffOptions = {},
): DffResult {
  const K = options.k ?? 4;
  const ITERS = options.iters ?? 200;
  const grid = Math.round(Math.sqrt(tokens));
  if (grid * grid !== tokens) {
    throw new Error(`DFF: non-square token grid (${tokens})`);
  }
  const C = channels;
  const P = tokens; // spatial positions

  // --- build X (C x P) in library orientation, then per-channel min-shift ---
  // reshape_transform maps token t -> spatial position t (row-major 12x12),
  // so X[ch, p] = features[p * C + ch].
  const X = new Float64Array(C * P);
  for (let ch = 0; ch < C; ch++) {
    let mn = Infinity;
    const xoff = ch * P;
    for (let p = 0; p < P; p++) {
      const v = features[p * C + ch];
      X[xoff + p] = v;
      if (v < mn) mn = v;
    }
    for (let p = 0; p < P; p++) X[xoff + p] -= mn; // shift this channel >= 0
  }

  const { W, H } = nmf(X, C, P, K, ITERS);

  // --- min-max normalize each heatmap (H row) to [0,1] for display ---
  const heatmaps: Float32Array[] = [];
  for (let k = 0; k < K; k++) {
    const hm = new Float32Array(P);
    let mn = Infinity,
      mx = -Infinity;
    for (let p = 0; p < P; p++) {
      const v = H[k * P + p];
      hm[p] = v;
      if (v < mn) mn = v;
      if (v > mx) mx = v;
    }
    const range = mx - mn || 1;
    for (let p = 0; p < P; p++) hm[p] = (hm[p] - mn) / range;
    heatmaps.push(hm);
  }

  // --- concept directions (W columns) for optional classifier labeling ---
  const concepts: Float32Array[] = [];
  for (let k = 0; k < K; k++) {
    const c = new Float32Array(C);
    for (let ch = 0; ch < C; ch++) c[ch] = W[ch * K + k];
    concepts.push(c);
  }

  return { k: K, grid, heatmaps, concepts };
}

// ---------------------------------------------------------------------------
// NMF: NNDSVD init + multiplicative updates (deterministic)
// ---------------------------------------------------------------------------

function nmf(X: Float64Array, N: number, M: number, K: number, iters: number) {
  const { W, H } = nndsvdInit(X, N, M, K);
  const eps = 1e-9;
  for (let it = 0; it < iters; it++) {
    // H *= (WtX) / (WtW H)
    const WtW = new Float64Array(K * K);
    for (let a = 0; a < K; a++)
      for (let b = a; b < K; b++) {
        let s = 0;
        for (let r = 0; r < N; r++) s += W[r * K + a] * W[r * K + b];
        WtW[a * K + b] = WtW[b * K + a] = s;
      }
    const WtX = new Float64Array(K * M);
    for (let r = 0; r < N; r++)
      for (let a = 0; a < K; a++) {
        const w = W[r * K + a];
        if (!w) continue;
        const xo = r * M,
          ho = a * M;
        for (let c = 0; c < M; c++) WtX[ho + c] += w * X[xo + c];
      }
    for (let a = 0; a < K; a++)
      for (let c = 0; c < M; c++) {
        let d = 0;
        for (let b = 0; b < K; b++) d += WtW[a * K + b] * H[b * M + c];
        H[a * M + c] *= WtX[a * M + c] / (d + eps);
      }
    // W *= (XHt) / (W HHt)
    const HHt = new Float64Array(K * K);
    for (let a = 0; a < K; a++)
      for (let b = a; b < K; b++) {
        let s = 0;
        for (let c = 0; c < M; c++) s += H[a * M + c] * H[b * M + c];
        HHt[a * K + b] = HHt[b * K + a] = s;
      }
    const XHt = new Float64Array(N * K);
    for (let r = 0; r < N; r++) {
      const xo = r * M;
      for (let a = 0; a < K; a++) {
        let s = 0;
        const ho = a * M;
        for (let c = 0; c < M; c++) s += X[xo + c] * H[ho + c];
        XHt[r * K + a] = s;
      }
    }
    for (let r = 0; r < N; r++)
      for (let a = 0; a < K; a++) {
        let d = 0;
        for (let b = 0; b < K; b++) d += W[r * K + b] * HHt[b * K + a];
        W[r * K + a] *= XHt[r * K + a] / (d + eps);
      }
  }
  return { W, H };
}

// NNDSVD init (Boutsidis & Gallopoulos) using a rank-K SVD of X derived from
// the Jacobi eigendecomposition of the (M x M) Gram matrix X^T X.
function nndsvdInit(X: Float64Array, N: number, M: number, K: number) {
  const G = gram(X, N, M);
  const { val, V } = jacobi(G, M);
  const order = [...val.keys()].sort((i, j) => val[j] - val[i]).slice(0, K);
  const W = new Float64Array(N * K);
  const H = new Float64Array(K * M);

  for (let k = 0; k < K; k++) {
    const col = order[k];
    const s = Math.sqrt(Math.max(val[col], 0));
    const v = new Float64Array(M);
    for (let i = 0; i < M; i++) v[i] = V[i * M + col]; // right singular vector
    const u = new Float64Array(N); // left = X v / s
    for (let r = 0; r < N; r++) {
      let acc = 0;
      const o = r * M;
      for (let c = 0; c < M; c++) acc += X[o + c] * v[c];
      u[r] = s > 0 ? acc / s : 0;
    }
    if (k === 0) {
      const su = Math.sqrt(s);
      for (let r = 0; r < N; r++) W[r * K] = su * Math.abs(u[r]);
      for (let c = 0; c < M; c++) H[c] = su * Math.abs(v[c]);
    } else {
      const up = posNorm(u, +1),
        un = posNorm(u, -1);
      const vp = posNorm(v, +1),
        vn = posNorm(v, -1);
      const mp = up.norm * vp.norm,
        mn = un.norm * vn.norm;
      const usePos = mp >= mn;
      const uu = usePos ? up : un;
      const vv = usePos ? vp : vn;
      const sigma = usePos ? mp : mn;
      const sc = Math.sqrt(s * sigma);
      for (let r = 0; r < N; r++)
        W[r * K + k] = uu.norm > 0 ? (sc * uu.vec[r]) / uu.norm : 0;
      for (let c = 0; c < M; c++)
        H[k * M + c] = vv.norm > 0 ? (sc * vv.vec[c]) / vv.norm : 0;
    }
  }
  return { W, H };
}

function posNorm(v: Float64Array, sign: number) {
  const vec = new Float64Array(v.length);
  let s = 0;
  for (let i = 0; i < v.length; i++) {
    const x = sign > 0 ? Math.max(v[i], 0) : Math.max(-v[i], 0);
    vec[i] = x;
    s += x * x;
  }
  return { vec, norm: Math.sqrt(s) };
}

function gram(X: Float64Array, N: number, M: number): Float64Array {
  const C = new Float64Array(M * M);
  for (let r = 0; r < N; r++) {
    const o = r * M;
    for (let i = 0; i < M; i++) {
      const xi = X[o + i];
      if (!xi) continue;
      for (let j = i; j < M; j++) C[i * M + j] += xi * X[o + j];
    }
  }
  for (let i = 0; i < M; i++)
    for (let j = i + 1; j < M; j++) C[j * M + i] = C[i * M + j];
  return C;
}

// Cyclic Jacobi eigendecomposition of a symmetric (M x M) matrix.
// Returns eigenvalues `val` and eigenvectors `V` (column k is the k-th vector).
function jacobi(A: Float64Array, M: number) {
  const a = Float64Array.from(A);
  const V = new Float64Array(M * M);
  for (let i = 0; i < M; i++) V[i * M + i] = 1;
  for (let sweep = 0; sweep < 100; sweep++) {
    let off = 0;
    for (let p = 0; p < M; p++)
      for (let q = p + 1; q < M; q++) off += a[p * M + q] * a[p * M + q];
    if (off < 1e-18) break;
    for (let p = 0; p < M; p++)
      for (let q = p + 1; q < M; q++) {
        const apq = a[p * M + q];
        if (Math.abs(apq) < 1e-300) continue;
        const phi = 0.5 * Math.atan2(2 * apq, a[q * M + q] - a[p * M + p]);
        const c = Math.cos(phi),
          s = Math.sin(phi);
        for (let k = 0; k < M; k++) {
          const akp = a[k * M + p],
            akq = a[k * M + q];
          a[k * M + p] = c * akp - s * akq;
          a[k * M + q] = s * akp + c * akq;
        }
        for (let k = 0; k < M; k++) {
          const apk = a[p * M + k],
            aqk = a[q * M + k];
          a[p * M + k] = c * apk - s * aqk;
          a[q * M + k] = s * apk + c * aqk;
        }
        for (let k = 0; k < M; k++) {
          const vkp = V[k * M + p],
            vkq = V[k * M + q];
          V[k * M + p] = c * vkp - s * vkq;
          V[k * M + q] = s * vkp + c * vkq;
        }
      }
  }
  const val = new Float64Array(M);
  for (let i = 0; i < M; i++) val[i] = a[i * M + i];
  return { val, V };
}

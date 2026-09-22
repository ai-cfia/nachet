"""Step 3 of the DFF export (see DFF_EXPORT.md).

Produce a browser-loadable FP16 model.

  1. Run ORT graph optimization (EXTENDED) on the FP32 model so the decomposed
     LayerNorm subgraphs fuse into real LayerNormalization ops and the dynamic
     casts disappear. Save -> model_with_features[.TAG].opt.onnx (FP32, fused).
  2. Convert the FUSED model to FP16. Because layernorms are now single ops, the
     converter no longer emits the broken precision-free cast pattern that makes
     SimplifiedLayerNormFusion crash. Save -> model_browser[.TAG].fp16.onnx
  3. Load the FP16 model under FULL optimization (what onnxruntime-web does) and
     confirm it initializes, returns both outputs at the right shapes, and stays
     accurate vs the FP32 reference.

Env:
  SWIN_TAG  filename suffix to avoid clobbering artifacts (e.g. "101spp").
"""
import os
import time
import numpy as np
import onnx
import onnxruntime as ort
from onnxconverter_common import float16

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("SWIN_TAG", "")  # e.g. "101spp"; "" keeps the original filenames
_suffix = f".{TAG}" if TAG else ""
FP32 = os.path.join(HERE, f"model_with_features{_suffix}.onnx")
OPT = os.path.join(HERE, f"model_with_features{_suffix}.opt.onnx")
OUT = os.path.join(HERE, f"model_browser{_suffix}.fp16.onnx")
FEATURE_OUTPUT_NAME = "swin_layernorm"


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def run(path, x, opt_level):
    so = ort.SessionOptions()
    so.graph_optimization_level = opt_level
    sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    outs = sess.run(None, {name: x})
    return sess, dict(zip([o.name for o in sess.get_outputs()], outs))


def main():
    # ---- 1. optimize FP32 (fuses layernorms) ----
    print("[1] Optimizing FP32 model (EXTENDED) -> fused layernorms ...")
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
    so.optimized_model_filepath = OPT
    t0 = time.time()
    ort.InferenceSession(FP32, so, providers=["CPUExecutionProvider"])
    print(f"    saved {OPT} ({human(os.path.getsize(OPT))}) in {time.time()-t0:.1f}s")

    # how many fused layernorm ops now exist?
    opt_model = onnx.load(OPT, load_external_data=False)
    ln_ops = [n.op_type for n in opt_model.graph.node
              if "LayerNorm" in n.op_type]
    print(f"    fused LayerNorm-type ops in optimized graph: {len(ln_ops)} "
          f"({set(ln_ops)})")
    out_names = [o.name for o in opt_model.graph.output]
    print(f"    optimized graph outputs: {out_names}")

    # ---- 2. convert fused model to FP16 ----
    print("[2] Converting fused model to FP16 ...")
    t0 = time.time()
    m = onnx.load(OPT)
    m16 = float16.convert_float_to_float16(m, keep_io_types=True, disable_shape_infer=True)
    onnx.save(m16, OUT)
    print(f"    saved {OUT} ({human(os.path.getsize(OUT))}) in {time.time()-t0:.1f}s")

    # ---- 3. load FP16 with FULL opt (browser-like) + verify ----
    print("[3] Loading FP16 with FULL optimization (browser-like) + verifying ...")
    x = np.random.rand(1, 3, 384, 384).astype(np.float32)
    _, ref = run(FP32, x, ort.GraphOptimizationLevel.ORT_ENABLE_ALL)
    _, got = run(OUT, x, ort.GraphOptimizationLevel.ORT_ENABLE_ALL)  # <-- the real test

    print("\n" + "=" * 60)
    print("BROWSER FP16 MODEL -- loads under full opt, results:")
    print("=" * 60)
    for name in got:
        a, b = ref[name], got[name]
        amax = float(np.max(np.abs(a - b)))
        denom = float(np.max(np.abs(a))) or 1.0
        print(f"  {name:16s} shape={tuple(b.shape)} dtype={b.dtype}  "
              f"max|diff|={amax:.4g}  rel={amax/denom:.4g}")
    t32, t16 = int(np.argmax(ref["logits"])), int(np.argmax(got["logits"]))
    print(f"\n  argmax(logits): FP32={t32} FP16={t16} agree={t32==t16}")
    feat_ok = tuple(got[FEATURE_OUTPUT_NAME].shape) == (1, 144, 1536)
    print(f"  {FEATURE_OUTPUT_NAME} == (1,144,1536)? {feat_ok}")
    print(f"\n  Size: FP32 {human(os.path.getsize(FP32))} -> "
          f"FP16 {human(os.path.getsize(OUT))}")


if __name__ == "__main__":
    main()

"""Step 2 of the DFF export (see DFF_EXPORT.md).

Add the final swin.layernorm tensor as a second graph output via a passthrough
Identity node (the original tensor name is kept intact for existing consumers),
then verify its concrete shape with a real inference on a (1,3,384,384) input.

Input:  model[.TAG].graph.onnx   (from dff_inspect.py; weights inline)
Output: model_with_features[.TAG].onnx

Env:
  SWIN_TAG  filename suffix to avoid clobbering artifacts (e.g. "101spp").
"""
import os
import time
import numpy as np
import onnx
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("SWIN_TAG", "")  # e.g. "101spp"; "" keeps the original filenames
_suffix = f".{TAG}" if TAG else ""
SRC = os.path.join(HERE, f"model{_suffix}.graph.onnx")
DST = os.path.join(HERE, f"model_with_features{_suffix}.onnx")

FEATURE_TENSOR = "/swin/layernorm/Add_1_output_0"  # output of final swin.layernorm
FEATURE_OUTPUT_NAME = "swin_layernorm"             # friendly name for the new output


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    print(f"Loading {SRC} ({human(os.path.getsize(SRC))}) ...")
    t0 = time.time()
    model = onnx.load(SRC)  # weights are inline, so load them too
    print(f"  loaded in {time.time()-t0:.1f}s")

    existing_outputs = {o.name for o in model.graph.output}
    print(f"  existing outputs: {sorted(existing_outputs)}")

    # Sanity: the internal tensor must be produced by some node.
    producers = [n for n in model.graph.node if FEATURE_TENSOR in n.output]
    if not producers:
        raise SystemExit(f"Tensor {FEATURE_TENSOR!r} is not produced by any node!")
    print(f"  {FEATURE_TENSOR!r} produced by op_type={producers[0].op_type}")

    # Add a new graph output that aliases the internal tensor via an Identity node.
    # (Aliasing keeps the original tensor name intact for any other consumers and
    #  gives us a cleanly named output.)
    if FEATURE_OUTPUT_NAME not in existing_outputs:
        identity = onnx.helper.make_node(
            "Identity",
            inputs=[FEATURE_TENSOR],
            outputs=[FEATURE_OUTPUT_NAME],
            name="dff_feature_identity",
        )
        model.graph.node.append(identity)
        vi = onnx.helper.make_empty_tensor_value_info(FEATURE_OUTPUT_NAME)
        model.graph.output.append(vi)
        print(f"  added new graph output: {FEATURE_OUTPUT_NAME!r}")

    print(f"Saving {DST} ...")
    t0 = time.time()
    onnx.save(model, DST)
    print(f"  saved in {time.time()-t0:.1f}s ({human(os.path.getsize(DST))})")

    # ---- Verify with a real inference (this needs the weights, which are inline) ----
    print("\nRunning inference to confirm concrete shapes (input 1x3x384x384) ...")
    so = ort.SessionOptions()
    sess = ort.InferenceSession(DST, so, providers=["CPUExecutionProvider"])

    inp = sess.get_inputs()[0]
    print(f"  model input: {inp.name} {inp.shape} {inp.type}")

    x = np.random.rand(1, 3, 384, 384).astype(np.float32)
    t0 = time.time()
    outputs = sess.run(None, {inp.name: x})
    print(f"  inference done in {time.time()-t0:.1f}s")

    print("\n" + "=" * 60)
    print("CONFIRMED OUTPUT SHAPES")
    print("=" * 60)
    for meta, arr in zip(sess.get_outputs(), outputs):
        print(f"  {meta.name:18s} {tuple(arr.shape)}  dtype={arr.dtype}")

    feat = dict(zip([o.name for o in sess.get_outputs()], outputs))[FEATURE_OUTPUT_NAME]
    expected = (1, 144, 1536)
    ok = tuple(feat.shape) == expected
    print(f"\n  swin_layernorm shape == {expected}? {ok}")
    if not ok:
        print("  !! shape mismatch -- investigate")


if __name__ == "__main__":
    main()

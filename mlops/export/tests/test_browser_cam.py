"""Exercise feature exposure and CAM head checks on a small ONNX graph."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
from safetensors.numpy import save_file

sys.path.insert(0, str(Path(__file__).parents[1]))
import browser_cam


class BrowserCamTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / "checkpoint"
        self.checkpoint.mkdir()
        (self.checkpoint / "config.json").write_text(json.dumps({
            "model_type": "swin", "id2label": {"0": "Beta", "1": "Alpha", "2": "Gamma"},
        }))
        self.weight = np.array([[1, 2, 3], [2, 0, 1], [-1, 0, 2]], dtype=np.float32)
        self.bias = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        save_file({"classifier.weight": self.weight, "classifier.bias": self.bias},
                  self.checkpoint / "model.safetensors")
        self.pixels = np.random.default_rng(42).random((1, 3, 2, 2)).astype(np.float32)
        graph = helper.make_graph([
            helper.make_node("Transpose", ["pixel_values"], ["nhwc"], perm=[0, 2, 3, 1]),
            helper.make_node("Reshape", ["nhwc", "shape"], [browser_cam.FEATURE_TENSOR]),
            helper.make_node("ReduceMean", [browser_cam.FEATURE_TENSOR], ["pooled"], axes=[1], keepdims=0),
            helper.make_node("Gemm", ["pooled", "weight", "bias"], ["logits"], transB=1),
        ], "cam-fixture", [helper.make_tensor_value_info("pixel_values", TensorProto.FLOAT, [1, 3, 2, 2])],
            [helper.make_tensor_value_info("logits", TensorProto.FLOAT, [1, 3])], initializer=[
                numpy_helper.from_array(np.array([1, 4, 3], dtype=np.int64), "shape"),
                numpy_helper.from_array(self.weight, "weight"),
                numpy_helper.from_array(self.bias, "bias"),
            ])
        self.source = self.root / "source.onnx"
        onnx.save(helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)], ir_version=10),
                  self.source)

    def test_fp16_features_and_row_order_are_preserved(self):
        browser, head = browser_cam.prepare_browser_model(
            self.source, self.checkpoint, self.root / "browser", self.pixels,
        )
        np.testing.assert_array_equal(np.fromfile(head, dtype="<f4").reshape(3, 3), self.weight)
        result = browser_cam.run(browser, self.pixels)
        expected = browser_cam.run(self.source, self.pixels)
        self.assertEqual(result["swin_layernorm"].shape, (1, 4, 3))
        self.assertEqual(result["swin_layernorm"].dtype, np.float32)
        np.testing.assert_allclose(result["logits"], expected["logits"], rtol=1e-2, atol=1e-3)

    def test_mismatched_head_does_not_produce_head_asset(self):
        save_file({"classifier.weight": self.weight + 2, "classifier.bias": self.bias},
                  self.checkpoint / "model.safetensors")
        output = self.root / "browser"
        with self.assertRaises(AssertionError):
            browser_cam.prepare_browser_model(self.source, self.checkpoint, output, self.pixels)
        self.assertFalse(list(output.glob("*.bin")))

    def test_nonfinite_graph_outputs_are_rejected(self):
        model = onnx.load(self.source)
        model.graph.initializer.append(numpy_helper.from_array(
            np.array(float("nan"), dtype=np.float32), "nan_factor",
        ))
        model.graph.node.insert(0, helper.make_node(
            "Mul", ["pixel_values", "nan_factor"], ["nonfinite_pixels"],
        ))
        model.graph.node[1].input[0] = "nonfinite_pixels"
        onnx.save(model, self.source)
        output = self.root / "browser"
        with self.assertRaisesRegex(ValueError, "non-finite outputs"):
            browser_cam.prepare_browser_model(
                self.source, self.checkpoint, output, self.pixels,
            )
        self.assertFalse((output / "model.onnx").exists())
        self.assertFalse(list(output.glob("*.bin")))

    def test_failed_precision_check_keeps_only_candidate(self):
        output = self.root / "browser"
        original_run = browser_cam.run

        def inaccurate_candidate(path, pixels):
            result = original_run(path, pixels)
            if Path(path).name == "model.candidate.onnx":
                result["logits"] = result["logits"] + 1
            return result

        with patch.object(browser_cam, "run", side_effect=inaccurate_candidate):
            with self.assertRaises(AssertionError):
                browser_cam.prepare_browser_model(
                    self.source, self.checkpoint, output, self.pixels,
                )
        self.assertTrue((output / "model.candidate.onnx").exists())
        self.assertFalse((output / "model.onnx").exists())
        self.assertFalse(list(output.glob("*.bin")))
        with self.assertRaises(FileExistsError):
            browser_cam.prepare_browser_model(
                self.source, self.checkpoint, output, self.pixels,
            )
        browser, _ = browser_cam.prepare_browser_model(
            self.source, self.checkpoint, self.root / "retry", self.pixels,
        )
        self.assertTrue(browser.is_file())

    def test_nonfinite_input_is_rejected_before_writing(self):
        output = self.root / "browser"
        self.pixels[0, 0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "nonempty and finite"):
            browser_cam.prepare_browser_model(
                self.source, self.checkpoint, output, self.pixels,
            )
        self.assertFalse(output.exists())

    def test_fused_normalization_output_is_supported(self):
        model = onnx.load(self.source)
        for node in model.graph.node:
            for names in (node.input, node.output):
                for i, name in enumerate(names):
                    if name == browser_cam.FEATURE_TENSOR:
                        names[i] = browser_cam.FUSED_FEATURE_TENSOR
        onnx.save(model, self.source)
        browser, _ = browser_cam.prepare_browser_model(
            self.source, self.checkpoint, self.root / "browser", self.pixels,
        )
        self.assertEqual(browser_cam.run(browser, self.pixels)["swin_layernorm"].shape, (1, 4, 3))

    def test_ambiguous_feature_outputs_are_rejected(self):
        model = onnx.load(self.source)
        model.graph.node.append(helper.make_node(
            "Identity", [browser_cam.FEATURE_TENSOR], [browser_cam.FUSED_FEATURE_TENSOR],
        ))
        onnx.save(model, self.source)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            browser_cam.add_feature_output(self.source, self.root / "features.onnx", 3)

    def test_missing_feature_tensor_is_rejected(self):
        model = onnx.load(self.source)
        model.graph.node[1].output[0] = "different_feature_tensor"
        onnx.save(model, self.source)
        with self.assertRaisesRegex(ValueError, "no final Swin feature tensor"):
            browser_cam.add_feature_output(self.source, self.root / "features.onnx", 3)

    def test_missing_label_row_is_rejected(self):
        (self.checkpoint / "config.json").write_text('{"model_type":"swin","id2label":{"0":"Beta"}}')
        with self.assertRaisesRegex(ValueError, "every classifier-head row"):
            browser_cam.load_classifier_head(self.checkpoint)

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "browser"
        output.mkdir()
        with self.assertRaises(FileExistsError):
            browser_cam.prepare_browser_model(self.source, self.checkpoint, output, self.pixels)


if __name__ == "__main__":
    unittest.main()

"""Exercise feature exposure and CAM head checks on a small ONNX graph."""

import hashlib
import json
from functools import partial
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
from safetensors.numpy import save_file

sys.path.insert(0, str(Path(__file__).parents[1]))
import browser_cam  # noqa: E402


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
            self.source, self.checkpoint, self.root / "browser", self.pixels, strict=True,
        )
        np.testing.assert_array_equal(np.fromfile(head, dtype="<f4").reshape(3, 3), self.weight)
        result = browser_cam.run_onnx(browser, self.pixels)
        expected = browser_cam.run_onnx(self.source, self.pixels)
        self.assertEqual(result["swin_layernorm"].shape, (1, 4, 3))
        self.assertEqual(result["swin_layernorm"].dtype, np.float32)
        np.testing.assert_allclose(result["logits"], expected["logits"], rtol=1e-2, atol=1e-3)
        self.assertEqual({path.name for path in browser.parent.iterdir()},
                         {"model.candidate.onnx", "classifier_head_3spp.f32.bin", "validation.json"})
        report = json.loads((browser.parent / "validation.json").read_text())
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["output_checks"], "passed")
        self.assertTrue(report["strict"])
        self.assertEqual(report["fp16_checks"], "passed")
        self.assertNotIn("fp16_mismatch", report)
        self.assertNotIn("error", report)
        self.assertEqual(report["release_evaluation"], "not_performed")
        self.assertEqual(report["pixels"]["sha256"], hashlib.sha256(self.pixels.tobytes()).hexdigest())
        self.assertEqual(report["pixels"]["shape"], [1, 3, 2, 2])
        self.assertEqual(report["criteria"], {"atol": 1e-3, "rtol": 1e-2, "require_same_top1": True})
        self.assertEqual(len(report["images"]), 1)
        self.assertFalse(report["images"][0]["top1_changed"])
        self.assertFalse(list(self.root.glob(".browser.*.partial")))

    def test_mismatched_head_does_not_produce_head_asset(self):
        save_file({"classifier.weight": self.weight + 2, "classifier.bias": self.bias},
                  self.checkpoint / "model.safetensors")
        output = self.root / "browser"
        with self.assertRaisesRegex(AssertionError, "features and checkpoint head"):
            browser_cam.prepare_browser_model(self.source, self.checkpoint, output, self.pixels)
        self.assertFalse(output.exists())
        partial, = self.root.glob(".browser.*.partial")
        self.assertTrue((partial / "diagnostics/model_with_features.onnx").exists())
        self.assertFalse(list(partial.rglob("*.bin")))

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
        self.assertFalse(output.exists())
        partial, = self.root.glob(".browser.*.partial")
        self.assertFalse(list(partial.rglob("*.bin")))

    def test_nonfinite_fp16_outputs_are_rejected_in_both_modes(self):
        original_convert = browser_cam.float16.convert_float_to_float16

        def introduce_infinity(*args, **kwargs):
            model = original_convert(*args, **kwargs)
            for node in model.graph.node:
                for index, name in enumerate(node.output):
                    if name == "logits":
                        node.output[index] = "finite_logits"
            model.graph.initializer.append(numpy_helper.from_array(
                np.array(float("inf"), dtype=np.float32), "infinity",
            ))
            model.graph.node.append(helper.make_node("Mul", ["finite_logits", "infinity"], ["logits"]))
            return model

        for strict in (False, True):
            with self.subTest(strict=strict):
                output = self.root / f"nonfinite-{strict}"
                with patch.object(browser_cam.float16, "convert_float_to_float16", side_effect=introduce_infinity):
                    with self.assertRaisesRegex(ValueError, "non-finite outputs"):
                        browser_cam.prepare_browser_model(
                            self.source, self.checkpoint, output, self.pixels, strict=strict,
                        )
                self.assertFalse(output.exists())
                partial_output, = self.root.glob(f".{output.name}.*.partial")
                report = json.loads((partial_output / "validation.json").read_text())
                self.assertEqual(report["output_checks"], "failed")
                self.assertEqual(report["fp16_checks"], "not_performed")
                self.assertFalse(list(partial_output.rglob("*.bin")))

    def test_cli_reports_near_tie_change_and_strict_mode_rejects_it(self):
        # These distinct FP32 scores round to a tie during real FP16 conversion.
        weight = np.zeros_like(self.weight)
        bias = np.array([1.0, 1.0001, 0.2], dtype=np.float32)
        save_file({"classifier.weight": weight, "classifier.bias": bias},
                  self.checkpoint / "model.safetensors")
        model = onnx.load(self.source)
        for initializer in model.graph.initializer:
            if initializer.name == "weight":
                initializer.CopyFrom(numpy_helper.from_array(weight, "weight"))
            elif initializer.name == "bias":
                initializer.CopyFrom(numpy_helper.from_array(bias, "bias"))
        onnx.save(model, self.source)

        feature_model = self.root / "reference.onnx"
        browser_cam.add_feature_output(self.source, feature_model, 3)
        reference = browser_cam.run_onnx(feature_model, self.pixels)
        pixels_path = self.root / "pixels.npy"
        np.save(pixels_path, self.pixels)

        for strict in (False, True):
            with self.subTest(strict=strict):
                output = self.root / f"browser-{strict}"
                command = [sys.executable, str(Path(browser_cam.__file__)),
                           "--onnx", str(self.source), "--checkpoint", str(self.checkpoint),
                           "--output", str(output), "--pixels", str(pixels_path)]
                if strict:
                    command.append("--strict")
                result = subprocess.run(command, capture_output=True, text=True)
                if strict:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("FP16 top-1 predictions", result.stderr)
                    self.assertFalse(output.exists())
                    report_dir, = self.root.glob(f".{output.name}.*.partial")
                    candidate_path = report_dir / "diagnostics/model.candidate.onnx"
                    self.assertFalse(list(report_dir.rglob("*.bin")))
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("FP16 numerical checks: failed", result.stdout)
                    self.assertIn("not approved for deployment", result.stdout)
                    self.assertIn("WARNING: FP16 numerical checks failed", result.stderr)
                    report_dir = output
                    candidate_path = output / "model.candidate.onnx"
                    self.assertTrue((output / "classifier_head_3spp.f32.bin").is_file())
                candidate = browser_cam.run_onnx(candidate_path, self.pixels)
                for name in ("logits", browser_cam.FEATURE_OUTPUT_NAME):
                    np.testing.assert_allclose(candidate[name], reference[name], atol=1e-3, rtol=1e-2)
                np.testing.assert_array_equal(reference["logits"].argmax(axis=-1), [1])
                np.testing.assert_array_equal(candidate["logits"].argmax(axis=-1), [0])
                report = json.loads((report_dir / "validation.json").read_text())
                image = report["images"][0]
                self.assertTrue(image["top1_changed"])
                self.assertTrue(image["ordered_top5_changed"])
                self.assertEqual(image["fp32_top5"], [1, 0, 2])
                self.assertEqual(image["fp16_top5"], [0, 1, 2])
                self.assertAlmostEqual(image["fp32_top1_margin"], 0.0001, places=6)
                for error in image["errors"].values():
                    self.assertEqual(error["values_outside_tolerance"], 0)
                self.assertEqual(report["output_checks"], "passed")
                self.assertEqual(report["fp16_checks"], "failed")
                self.assertEqual(report["strict"], strict)
                self.assertEqual(report["release_evaluation"], "not_performed")
                self.assertIn("top-1 predictions", report["fp16_mismatch"])
                self.assertEqual("error" in report, strict)
                self.assertFalse((output / "model.onnx").exists())

    def test_output_names_shapes_and_types_must_match(self):
        reference = {
            "logits": np.ones((1, 3), dtype=np.float32),
            "swin_layernorm": np.ones((1, 4, 3), dtype=np.float32),
        }
        cases = [
            ("missing", {"logits": reference["logits"]}, "output names"),
            ("extra", {**reference, "extra": reference["logits"]}, "output names"),
            ("shape", {**reference, "logits": reference["logits"][0]}, "shape"),
            ("dtype", {**reference, "logits": reference["logits"].astype(np.float16)}, "float32"),
        ]
        for strict in (False, True):
            for name, outputs, message in cases:
                with self.subTest(case=name, strict=strict):
                    report_path = self.root / f"{name}-{strict}.json"
                    with patch.object(browser_cam, "run_onnx", return_value=outputs):
                        with self.assertRaisesRegex(ValueError, message):
                            browser_cam.verify_fp16(self.source, self.pixels, reference, report_path, strict=strict)
                    report = json.loads(report_path.read_text())
                    self.assertEqual(report["output_checks"], "failed")
                    self.assertEqual(report["fp16_checks"], "not_performed")
                    self.assertIn(message, report["error"])

    def test_report_write_failure_prevents_final_output(self):
        original_write = Path.write_text

        def fail_report(path, *args, **kwargs):
            if path.name == "validation.json":
                raise OSError("report write failed")
            return original_write(path, *args, **kwargs)

        output = self.root / "browser"
        with patch.object(Path, "write_text", autospec=True, side_effect=fail_report):
            with self.assertRaisesRegex(OSError, "report write failed"):
                browser_cam.prepare_browser_model(self.source, self.checkpoint, output, self.pixels)
        self.assertFalse(output.exists())
        partial, = self.root.glob(".browser.*.partial")
        self.assertFalse(list(partial.rglob("*.bin")))

    def test_conversion_defects_are_reported_and_strict_mode_rejects_them(self):
        original_convert = browser_cam.float16.convert_float_to_float16

        def damage_graph(fault, *args, **kwargs):
            model = original_convert(*args, **kwargs)
            if fault == "zeroed_weights":
                weights, = [value for value in model.graph.initializer if tuple(value.dims) == (3, 3)]
                weights.CopyFrom(numpy_helper.from_array(np.zeros_like(numpy_helper.to_array(weights)), weights.name))
                return model
            name = "logits" if fault == "permuted_logits" else browser_cam.FEATURE_OUTPUT_NAME
            for node in model.graph.node:
                for index, output_name in enumerate(node.output):
                    if output_name == name:
                        node.output[index] = "before_fault"
            if fault == "permuted_logits":
                model.graph.initializer.append(numpy_helper.from_array(np.array([2, 0, 1], dtype=np.int64), "order"))
                node = helper.make_node("Gather", ["before_fault", "order"], [name], axis=1)
            else:
                model.graph.initializer.append(numpy_helper.from_array(np.array(1.2, dtype=np.float32), "scale"))
                node = helper.make_node("Mul", ["before_fault", "scale"], [name])
            model.graph.node.append(node)
            return model

        for fault in ("permuted_logits", "scaled_features", "zeroed_weights"):
            with self.subTest(fault=fault):
                output = self.root / fault
                with patch.object(browser_cam.float16, "convert_float_to_float16",
                                  side_effect=partial(damage_graph, fault)):
                    with self.assertRaisesRegex(AssertionError, "differs from the FP32 reference") as failure:
                        browser_cam.prepare_browser_model(self.source, self.checkpoint, output, self.pixels, strict=True)
                self.assertFalse(output.exists())
                partial_output, = self.root.glob(f".{fault}.*.partial")
                report = json.loads((partial_output / "validation.json").read_text())
                self.assertEqual(report["output_checks"], "passed")
                self.assertTrue(report["strict"])
                self.assertEqual(report["fp16_checks"], "failed")
                name = browser_cam.FEATURE_OUTPUT_NAME if fault == "scaled_features" else "logits"
                self.assertGreater(report["images"][0]["errors"][name]["values_outside_tolerance"], 0)
                self.assertFalse(list(partial_output.rglob("*.bin")))
                self.assertIn(str(partial_output), "\n".join(failure.exception.__notes__))

                candidate_output = self.root / f"{fault}-candidate"
                with patch.object(browser_cam.float16, "convert_float_to_float16",
                                  side_effect=partial(damage_graph, fault)):
                    candidate, _ = browser_cam.prepare_browser_model(
                        self.source, self.checkpoint, candidate_output, self.pixels,
                    )
                self.assertEqual(candidate.name, "model.candidate.onnx")
                self.assertTrue(candidate.is_file())
                self.assertFalse((candidate_output / "model.onnx").exists())
                candidate_report = json.loads((candidate_output / "validation.json").read_text())
                self.assertEqual(candidate_report["fp16_checks"], "failed")
                self.assertEqual(candidate_report["release_evaluation"], "not_performed")
                self.assertEqual(candidate_report["images"], report["images"])
                self.assertIn("differs from the FP32 reference", candidate_report["fp16_mismatch"])
                self.assertNotIn("error", candidate_report)

                # Exercise recovery once; every fault above still checks rejection.
                if fault == "scaled_features":
                    candidate = partial_output / "diagnostics/model.candidate.onnx"
                    failed_graph = candidate.read_bytes()
                    browser, _ = browser_cam.prepare_browser_model(
                        self.source, self.checkpoint, output, self.pixels, strict=True,
                    )
                    self.assertTrue(browser.is_file())
                    self.assertEqual(candidate.read_bytes(), failed_graph)

    def test_report_keeps_separate_measurements_for_each_image(self):
        model = onnx.load(self.source)
        model.graph.input[0].type.tensor_type.shape.dim[0].dim_param = "batch"
        model.graph.output[0].type.tensor_type.shape.dim[0].dim_param = "batch"
        for initializer in model.graph.initializer:
            if initializer.name == "shape":
                initializer.CopyFrom(numpy_helper.from_array(np.array([-1, 4, 3], dtype=np.int64), "shape"))
        onnx.save(model, self.source)
        pixels = np.concatenate([self.pixels, np.zeros_like(self.pixels)])
        browser, _ = browser_cam.prepare_browser_model(self.source, self.checkpoint, self.root / "browser", pixels)
        report = json.loads((browser.parent / "validation.json").read_text())
        first, second = report["images"]
        self.assertEqual([first["index"], second["index"]], [0, 1])
        self.assertEqual(first["fp32_top5"][0], 0)
        self.assertEqual(second["fp32_top5"][0], 2)
        self.assertGreater(first["errors"]["swin_layernorm"]["reference_l2"], 0)
        self.assertIsNone(second["errors"]["swin_layernorm"]["relative_l2_error"])
        self.assertEqual(second["errors"]["swin_layernorm"]["error_l2"], 0)

    def test_error_metrics_preserve_zero_reference_and_large_finite_values(self):
        reference = np.array([3, 4], dtype=np.float32)
        actual = np.array([0, 0], dtype=np.float32)
        errors = browser_cam.output_errors(reference, actual)
        self.assertEqual(errors["reference_l2"], 5)
        self.assertEqual(errors["error_l2"], 5)
        self.assertEqual(errors["relative_l2_error"], 1)
        self.assertEqual(errors["max_absolute_error"], 4)
        self.assertEqual(errors["values_outside_tolerance"], 2)
        for actual in (np.zeros(2, dtype=np.float32), np.ones(2, dtype=np.float32),
                       np.full(2, np.finfo(np.float32).max, dtype=np.float32)):
            with self.subTest(actual=actual):
                errors = browser_cam.output_errors(np.zeros(2, dtype=np.float32), actual)
                self.assertIsNone(errors["relative_l2_error"])
                self.assertTrue(np.isfinite(errors["error_l2"]))
                json.dumps(errors, allow_nan=False)

    def test_nonfinite_input_is_rejected_before_writing(self):
        output = self.root / "browser"
        self.pixels[0, 0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "nonempty and finite"):
            browser_cam.prepare_browser_model(
                self.source, self.checkpoint, output, self.pixels,
            )
        self.assertFalse(output.exists())

    def test_fused_feature_tensor_name_is_recognized(self):
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
        self.assertEqual(browser_cam.run_onnx(browser, self.pixels)["swin_layernorm"].shape, (1, 4, 3))

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

    def test_head_requires_a_weight_matrix_and_one_bias_per_class(self):
        cases = [
            (self.weight[0], self.bias, "weights must be a two-dimensional matrix"),
            (self.weight, self.bias[:2], "Classifier bias must have shape"),
            (self.weight, self.bias.reshape(3, 1), "Classifier bias must have shape"),
        ]
        for weight, bias, message in cases:
            with self.subTest(weight_shape=weight.shape, bias_shape=bias.shape):
                save_file({"classifier.weight": weight, "classifier.bias": bias},
                          self.checkpoint / "model.safetensors")
                with self.assertRaisesRegex(ValueError, message):
                    browser_cam.load_classifier_head(self.checkpoint)

    def test_single_weight_file_takes_precedence_over_stale_index(self):
        (self.checkpoint / "model.safetensors.index.json").write_text(json.dumps({
            "weight_map": {"classifier.weight": "missing.safetensors",
                           "classifier.bias": "missing.safetensors"},
        }))
        weights, bias = browser_cam.load_classifier_head(self.checkpoint)
        np.testing.assert_array_equal(weights, self.weight)
        np.testing.assert_array_equal(bias, self.bias)

    def test_head_can_span_two_real_weight_shards(self):
        (self.checkpoint / "model.safetensors").unlink()
        save_file({"classifier.weight": self.weight}, self.checkpoint / "weight.safetensors")
        save_file({"classifier.bias": self.bias}, self.checkpoint / "bias.safetensors")
        (self.checkpoint / "model.safetensors.index.json").write_text(json.dumps({
            "weight_map": {"classifier.weight": "weight.safetensors",
                           "classifier.bias": "bias.safetensors"},
        }))
        weights, bias = browser_cam.load_classifier_head(self.checkpoint)
        np.testing.assert_array_equal(weights, self.weight)
        np.testing.assert_array_equal(bias, self.bias)

    def test_bfloat16_head_loads_as_float32_from_single_file_or_shards(self):
        import torch
        from safetensors.torch import save_file as save_torch_file

        weight = torch.from_numpy(self.weight).bfloat16()
        bias = torch.from_numpy(self.bias).bfloat16()
        for sharded in (False, True):
            with self.subTest(sharded=sharded):
                if sharded:
                    (self.checkpoint / "model.safetensors").unlink()
                    save_torch_file({"classifier.weight": weight}, self.checkpoint / "weight.safetensors")
                    save_torch_file({"classifier.bias": bias}, self.checkpoint / "bias.safetensors")
                    (self.checkpoint / "model.safetensors.index.json").write_text(json.dumps({
                        "weight_map": {"classifier.weight": "weight.safetensors",
                                       "classifier.bias": "bias.safetensors"},
                    }))
                else:
                    save_torch_file({"classifier.weight": weight, "classifier.bias": bias},
                                    self.checkpoint / "model.safetensors")
                actual_weight, actual_bias = browser_cam.load_classifier_head(self.checkpoint)
                self.assertEqual(actual_weight.dtype, np.float32)
                self.assertEqual(actual_bias.dtype, np.float32)
                np.testing.assert_array_equal(actual_weight, weight.float().numpy())
                np.testing.assert_array_equal(actual_bias, bias.float().numpy())

    def test_missing_head_tensor_has_an_explicit_error(self):
        save_file({"classifier.weight": self.weight}, self.checkpoint / "model.safetensors")
        with self.assertRaisesRegex(ValueError, "Missing 'classifier.bias'"):
            browser_cam.load_classifier_head(self.checkpoint)

    def test_missing_head_index_entry_has_an_explicit_error(self):
        (self.checkpoint / "model.safetensors").rename(self.checkpoint / "shard.safetensors")
        (self.checkpoint / "model.safetensors.index.json").write_text(json.dumps({
            "weight_map": {"classifier.weight": "shard.safetensors"},
        }))
        with self.assertRaisesRegex(ValueError, "Weight index has no entry for 'classifier.bias'"):
            browser_cam.load_classifier_head(self.checkpoint)

    def test_cli_help_works_for_direct_and_module_invocation(self):
        script = Path(browser_cam.__file__).resolve()
        for arguments in ([str(script)], ["-m", "mlops.export.browser_cam"]):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, *arguments, "--help"], cwd=script.parents[2],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--pixels", result.stdout)
                self.assertIn("--strict", result.stdout)

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "browser"
        output.mkdir()
        sentinel = output / "keep"
        sentinel.write_bytes(b"existing export")
        with self.assertRaises(FileExistsError):
            browser_cam.prepare_browser_model(self.source, self.checkpoint, output, self.pixels)
        self.assertEqual(sentinel.read_bytes(), b"existing export")
        self.assertFalse(list(self.root.glob(".browser.*.partial")))


if __name__ == "__main__":
    unittest.main()

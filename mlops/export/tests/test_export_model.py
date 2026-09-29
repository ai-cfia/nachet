"""Local export boundaries and offline Swin, CAM and detector integration tests."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import export_model  # noqa: E402


def create_swin_fixture(root):
    """Use the same tiny model and processed image for FP32 and CAM checks."""
    import numpy as np
    import torch
    from PIL import Image
    from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor

    torch.manual_seed(42)
    torch.set_num_threads(1)
    model = SwinForImageClassification(SwinConfig(
        image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
        num_heads=[1, 2], window_size=2, num_labels=3,
        id2label={0: "Beta", 1: "Alpha", 2: "Gamma"},
        label2id={"Beta": 0, "Alpha": 1, "Gamma": 2},
    )).eval()
    processor = ViTImageProcessor(size={"height": 32, "width": 32})
    checkpoint = root / "checkpoint"
    model.save_pretrained(checkpoint)
    processor.save_pretrained(checkpoint)
    image = Image.fromarray(np.random.default_rng(42).integers(
        0, 256, size=(48, 40, 3), dtype=np.uint8,
    ))
    pixels = processor(images=image, return_tensors="pt")["pixel_values"]
    return model, checkpoint, pixels


class StagedOutputTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "export"

    def test_interrupted_run_retains_diagnostics_and_can_retry(self):
        with self.assertRaises(KeyboardInterrupt) as failure:
            with export_model.staged_output(self.output) as staging:
                (staging / "diagnostic").write_bytes(b"keep")
                raise KeyboardInterrupt()
        self.assertFalse(self.output.exists())
        self.assertIn(str(staging), "\n".join(failure.exception.__notes__))
        with export_model.staged_output(self.output) as retry:
            self.assertNotEqual(retry, staging)
            (retry / "model.onnx").write_bytes(b"model")
        self.assertEqual((staging / "diagnostic").read_bytes(), b"keep")

    def test_existing_paths_are_rejected(self):
        for kind in ("empty_directory", "file", "dangling_symlink"):
            with self.subTest(kind=kind):
                output = self.root / kind
                if kind == "empty_directory":
                    output.mkdir()
                elif kind == "file":
                    output.write_bytes(b"keep")
                else:
                    output.symlink_to(self.root / "missing", target_is_directory=True)
                before = output.lstat()
                with self.assertRaises(FileExistsError):
                    with export_model.staged_output(output):
                        self.fail("An existing destination was accepted")
                self.assertEqual(output.lstat().st_ino, before.st_ino)
                self.assertFalse(list(self.root.glob(f".{kind}.*.partial")))

    def test_destination_created_during_export_is_not_replaced(self):
        with self.assertRaises(FileExistsError):
            with export_model.staged_output(self.output) as staging:
                (staging / "model.onnx").write_bytes(b"model")
                self.output.mkdir()
                destination_inode = self.output.stat().st_ino
        self.assertEqual(self.output.stat().st_ino, destination_inode)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual((staging / "model.onnx").read_bytes(), b"model")


class ExportBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / "checkpoint-1"
        self.checkpoint.mkdir()
        (self.checkpoint / "config.json").write_text(json.dumps({"model_type": "swin"}))
        (self.checkpoint / "model.safetensors").write_bytes(b"test weights")
        (self.checkpoint / "preprocessor_config.json").write_text("{}")
        (self.checkpoint / "optimizer.pt").write_bytes(b"not an export input")
        self.output = self.root / "export"

    def fake_run(self, command, **kwargs):
        self.assertTrue(kwargs["check"])
        self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
        destination = Path(command[-1])
        destination.mkdir()
        if command[1] == "export":
            source = Path(command[command.index("--model") + 1])
            self.assertEqual({p.name for p in source.iterdir()}, {
                "config.json", "model.safetensors", "preprocessor_config.json",
            })
            (destination / "model.onnx").write_bytes(b"test graph")
        else:
            self.assertIn("--avx512", command)
            (destination / "model_quantized.onnx").write_bytes(b"test quantized graph")

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_export_failure_stops_before_quantization(self, _):
        with patch.object(export_model.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "export")) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                export_model.export_model(self.checkpoint, self.output, quantize=True)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(self.output.exists())

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_quantization_failure_retains_partial_runs_and_allows_retry(self, _):
        def fail_quantization(command, **kwargs):
            if command[1] == "export":
                self.fake_run(command, **kwargs)
            else:
                destination = Path(command[-1])
                destination.mkdir()
                (destination / "incomplete").write_bytes(b"partial quantization")
                raise subprocess.CalledProcessError(1, command)

        with patch.object(export_model.subprocess, "run", side_effect=fail_quantization):
            with self.assertRaises(subprocess.CalledProcessError):
                export_model.export_model(self.checkpoint, self.output, quantize=True)
        self.assertFalse(self.output.exists())
        partial, = self.root.glob(".export.*.partial")
        self.assertEqual((partial / "onnx-fp32/model.onnx").read_bytes(), b"test graph")
        self.assertEqual((partial / "onnx-quant/incomplete").read_bytes(), b"partial quantization")
        with patch.object(export_model.subprocess, "run", side_effect=self.fake_run):
            export_model.export_model(self.checkpoint, self.output, quantize=True)
        self.assertTrue((self.output / "onnx-quant/model_quantized.onnx").is_file())
        self.assertTrue(partial.is_dir())

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_success_exit_without_graph_is_rejected(self, _):
        with patch.object(export_model.subprocess, "run"):
            with self.assertRaisesRegex(FileNotFoundError, "Export command did not produce onnx-fp32/model[.]onnx"):
                export_model.export_model(self.checkpoint, self.output)

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_existing_output_is_not_overwritten(self, _):
        self.output.mkdir()
        sentinel = self.output / "keep"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(FileExistsError, "Export output already exists"):
            export_model.export_model(self.checkpoint, self.output)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_output_cannot_mutate_checkpoint(self):
        with self.assertRaisesRegex(ValueError, "outside the source checkpoint"):
            export_model.export_model(self.checkpoint, self.checkpoint / "onnx")

    def test_missing_processor_is_rejected(self):
        with self.assertRaisesRegex(FileNotFoundError, "Missing .*preprocessor_config[.]json"):
            export_model.export_model(self.checkpoint, self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_unknown_model_type_is_rejected(self):
        (self.checkpoint / "config.json").write_text('{"model_type":"unknown"}')
        with self.assertRaisesRegex(ValueError, "Unsupported model type: 'unknown'"):
            export_model.export_model(self.checkpoint, self.output)
        self.assertFalse(self.output.exists())

    def test_shard_index_rejects_paths_outside_checkpoint(self):
        (self.checkpoint / "model.safetensors").unlink()
        (self.checkpoint / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {"weight": "../other.safetensors"}})
        )
        with self.assertRaisesRegex(ValueError, "Invalid weight shard name"):
            export_model.checkpoint_files(self.checkpoint)

    def test_missing_weight_shard_is_rejected(self):
        (self.checkpoint / "model.safetensors").unlink()
        (self.checkpoint / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {"layer.weight": "missing.safetensors"}})
        )
        with self.assertRaises(FileNotFoundError) as failure:
            export_model.checkpoint_files(self.checkpoint)
        self.assertEqual(failure.exception.args[0], self.checkpoint / "missing.safetensors")

    def test_malformed_weight_map_has_an_explicit_error(self):
        (self.checkpoint / "model.safetensors").unlink()
        for index in ({}, [], {"weight_map": []}, {"weight_map": {"weight": None}}):
            with self.subTest(index=index):
                (self.checkpoint / "model.safetensors.index.json").write_text(json.dumps(index))
                with self.assertRaisesRegex(ValueError, "Weight index must"):
                    export_model.checkpoint_files(self.checkpoint)


class SwinExportTest(unittest.TestCase):
    def test_sharded_checkpoint_and_separate_processor_round_trip(self):
        import numpy as np
        import onnx
        import onnxruntime as ort
        import torch
        from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor

        torch.manual_seed(7)
        torch.set_num_threads(1)
        model = SwinForImageClassification(SwinConfig(
            image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
            num_heads=[1, 2], window_size=2, num_labels=3,
            id2label={0: "Beta", 1: "Alpha", 2: "Gamma"},
        )).eval()
        processor = ViTImageProcessor(size={"height": 32, "width": 32})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint, processor_dir = root / "checkpoint", root / "processor"
            model.save_pretrained(checkpoint, max_shard_size="1KB")
            processor.save_pretrained(processor_dir)
            self.assertTrue((checkpoint / "model.safetensors.index.json").is_file())
            self.assertGreater(len(list(checkpoint.glob("*.safetensors"))), 1)
            self.assertFalse((checkpoint / "preprocessor_config.json").exists())
            (checkpoint / "optimizer.pt").write_bytes(b"training state")
            before = {path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in root.rglob("*") if path.is_file()}

            command = [sys.executable, str(Path(export_model.__file__)),
                       "--checkpoint", str(checkpoint), "--processor", str(processor_dir),
                       "--output", str(root / "export"), "--quantize"]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            fp32_dir = root / "export/onnx-fp32"
            runtime = ort.InferenceSession(str(fp32_dir / "model.onnx"),
                                           providers=["CPUExecutionProvider"])
            exported_processor = ViTImageProcessor.from_pretrained(fp32_dir, local_files_only=True)
            rng = np.random.default_rng(7)
            image = rng.integers(0, 256, size=(41, 27, 3), dtype=np.uint8)
            pixels = processor(images=image, return_tensors="np")["pixel_values"]
            np.testing.assert_array_equal(
                pixels, exported_processor(images=image, return_tensors="np")["pixel_values"],
            )
            for batch in (pixels, np.ones_like(pixels), np.concatenate([pixels, -pixels])):
                with torch.no_grad():
                    expected = model(pixel_values=torch.from_numpy(batch)).logits.numpy()
                actual = runtime.run(["logits"], {"pixel_values": batch})[0]
                np.testing.assert_allclose(actual, expected, atol=1e-5, rtol=1e-4)
            config = json.loads((fp32_dir / "config.json").read_text())
            self.assertEqual(config["id2label"], {"0": "Beta", "1": "Alpha", "2": "Gamma"})

            # INT8 is checked for executable output, not assumed to retain FP32 accuracy.
            quantized = root / "export/onnx-quant/model_quantized.onnx"
            graph = onnx.load(quantized)
            self.assertTrue(any(tensor.data_type == onnx.TensorProto.INT8
                                for tensor in graph.graph.initializer))
            quant_runtime = ort.InferenceSession(str(quantized), providers=["CPUExecutionProvider"])
            scores = quant_runtime.run(["logits"], {"pixel_values": pixels})[0]
            self.assertEqual(scores.shape, (1, 3))
            self.assertTrue(np.isfinite(scores).all())
            self.assertFalse(list((root / "export").rglob("optimizer.pt")))
            self.assertFalse(list(root.glob(".export.*.partial")))
            # Match ordinary directory permissions under the current process umask.
            self.assertEqual((root / "export").stat().st_mode, checkpoint.stat().st_mode)
            after = {path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
                     for directory in (checkpoint, processor_dir)
                     for path in directory.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_fp32_export_matches_pytorch_on_same_pixels(self):
        import numpy as np
        import onnxruntime as ort
        import torch

        with tempfile.TemporaryDirectory() as tmp:
            model, checkpoint, pixels = create_swin_fixture(Path(tmp))
            output = export_model.export_model(checkpoint, Path(tmp) / "export")
            graph = output / "onnx-fp32" / "model.onnx"
            session = ort.InferenceSession(str(graph), providers=["CPUExecutionProvider"])
            with torch.no_grad():
                expected = model(pixel_values=pixels).logits.numpy()
            actual = session.run(["logits"], {"pixel_values": pixels.numpy()})[0]
            np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-5)
            self.assertEqual(json.loads((graph.parent / "config.json").read_text())["id2label"],
                             {"0": "Beta", "1": "Alpha", "2": "Gamma"})

    def test_fp16_cam_candidate_preserves_assets_and_reports_precision_loss(self):
        import numpy as np
        import torch
        import browser_cam

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model, checkpoint, pixels = create_swin_fixture(root)
            output = export_model.export_model(checkpoint, root / "export")
            graph = output / "onnx-fp32/model.onnx"
            with torch.no_grad():
                expected = model(pixel_values=pixels).logits.numpy()

            browser, head = browser_cam.prepare_browser_model(
                graph, checkpoint, root / "browser", pixels.numpy(),
            )
            np.testing.assert_array_equal(
                np.fromfile(head, dtype="<f4").reshape(model.classifier.weight.shape),
                model.classifier.weight.detach().numpy(),
            )
            result = browser_cam.run_onnx(browser, pixels.numpy())
            self.assertEqual(result["swin_layernorm"].shape, (1, 16, 16))
            np.testing.assert_allclose(result["logits"], expected, rtol=1e-2, atol=1e-3)

            # This fixture exceeds the feature tolerance. Export must report it, not hide it.
            report = json.loads((browser.parent / "validation.json").read_text())
            self.assertEqual(report["output_checks"], "passed")
            self.assertEqual(report["fp16_checks"], "failed")
            self.assertFalse(report["strict"])
            self.assertEqual(report["release_evaluation"], "not_performed")
            feature_model = root / "reference.onnx"
            browser_cam.add_feature_output(graph, feature_model, model.classifier.weight.shape[1])
            reference = browser_cam.run_onnx(feature_model, pixels.numpy())
            outside_tolerance = ~np.isclose(
                result["swin_layernorm"], reference["swin_layernorm"], atol=1e-3, rtol=1e-2,
            )
            self.assertGreater(np.count_nonzero(outside_tolerance), 0)
            self.assertEqual(report["images"][0]["errors"]["swin_layernorm"]["values_outside_tolerance"],
                             int(np.count_nonzero(outside_tolerance)))
            with self.assertRaisesRegex(AssertionError, "FP16 swin_layernorm differs"):
                browser_cam.verify_fp16(browser, pixels.numpy(), reference, root / "strict.json", strict=True)
            strict_report = json.loads((root / "strict.json").read_text())
            self.assertTrue(strict_report["strict"])
            self.assertEqual(strict_report["fp16_checks"], "failed")
            self.assertEqual(strict_report["images"], report["images"])


class DetectorExportTest(unittest.TestCase):
    def test_logits_and_boxes_match_pytorch(self):
        import numpy as np
        import onnxruntime as ort
        import torch
        from transformers import (RTDetrResNetConfig, RTDetrV2Config,
                                  RTDetrV2ForObjectDetection, RTDetrImageProcessor)

        torch.manual_seed(42)
        torch.set_num_threads(1)
        backbone = RTDetrResNetConfig(
            embedding_size=16, hidden_sizes=[16, 32, 64, 128],
            depths=[1, 1, 1, 1], layer_type="basic", out_indices=[2, 3, 4],
        )
        model = RTDetrV2ForObjectDetection(RTDetrV2Config(
            backbone_config=backbone, encoder_in_channels=[32, 64, 128],
            encoder_hidden_dim=32, encoder_ffn_dim=64, encoder_attention_heads=4,
            d_model=32, decoder_in_channels=[32, 32, 32], decoder_ffn_dim=64,
            decoder_attention_heads=4, decoder_layers=2, num_queries=10,
            num_denoising=0, num_labels=1, id2label={0: "seed"},
            label2id={"seed": 0}, disable_custom_kernels=True,
        )).eval()
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "checkpoint"
            model.save_pretrained(checkpoint)
            RTDetrImageProcessor(size={"height": 64, "width": 64}).save_pretrained(checkpoint)
            output = export_model.export_model(checkpoint, Path(tmp) / "export")
            session = ort.InferenceSession(str(output / "onnx-fp32" / "model.onnx"),
                                           providers=["CPUExecutionProvider"])
            pixels = torch.rand(1, 3, 64, 64)
            for name, batch in {
                "random": pixels,
                "constant": torch.ones_like(pixels),
                "two_images": torch.cat([pixels, 1 - pixels]),
            }.items():
                with self.subTest(input=name):
                    with torch.no_grad():
                        expected = model(pixel_values=batch)
                    logits, boxes = session.run(
                        ["logits", "pred_boxes"], {"pixel_values": batch.numpy()},
                    )
                    np.testing.assert_allclose(logits, expected.logits.numpy(), rtol=1e-4, atol=1e-5)
                    np.testing.assert_allclose(boxes, expected.pred_boxes.numpy(), rtol=1e-4, atol=1e-5)


if __name__ == "__main__":
    unittest.main()

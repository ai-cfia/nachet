"""Local checkpoint export boundaries and a tiny offline Swin export."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import export_model


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
            (destination / "model_quantized.onnx").write_bytes(b"test quantized graph")

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_task_and_quantization_commands(self, _):
        for model_type, task in export_model.TASKS.items():
            with self.subTest(model_type=model_type):
                (self.checkpoint / "config.json").write_text(json.dumps({"model_type": model_type}))
                before = {p.name: p.read_bytes() for p in self.checkpoint.iterdir()}
                with patch.object(export_model.subprocess, "run", side_effect=self.fake_run) as run:
                    export_model.export_model(self.checkpoint, self.root / model_type, quantize=True)
                command = run.call_args_list[0].args[0]
                self.assertEqual(command[command.index("--task") + 1], task)
                self.assertIn("--avx512", run.call_args_list[1].args[0])
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.checkpoint.iterdir()})

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_export_failure_stops_before_quantization(self, _):
        with patch.object(export_model.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "export")) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                export_model.export_model(self.checkpoint, self.output, quantize=True)
        self.assertEqual(run.call_count, 1)

    @patch.object(export_model, "which", return_value="optimum-cli")
    def test_success_exit_without_graph_is_rejected(self, _):
        with patch.object(export_model.subprocess, "run"):
            with self.assertRaises(FileNotFoundError):
                export_model.export_model(self.checkpoint, self.output)

    def test_existing_output_is_not_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "keep"
        sentinel.write_text("keep")
        with self.assertRaises(FileExistsError):
            export_model.export_model(self.checkpoint, self.output)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_output_cannot_mutate_checkpoint(self):
        with self.assertRaises(ValueError):
            export_model.export_model(self.checkpoint, self.checkpoint / "onnx")

    def test_missing_processor_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            export_model.export_model(self.checkpoint, self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_unknown_model_type_is_rejected(self):
        (self.checkpoint / "config.json").write_text('{"model_type":"unknown"}')
        with self.assertRaises(ValueError):
            export_model.export_model(self.checkpoint, self.output)
        self.assertFalse(self.output.exists())

    def test_shard_index_rejects_paths_outside_checkpoint(self):
        (self.checkpoint / "model.safetensors").unlink()
        (self.checkpoint / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {"weight": "../other.safetensors"}})
        )
        with self.assertRaises(ValueError):
            export_model.checkpoint_files(self.checkpoint)

    def test_sharded_checkpoint_includes_each_weight_file_once(self):
        (self.checkpoint / "model.safetensors").unlink()
        index_file = self.checkpoint / "model.safetensors.index.json"
        index_file.write_text(json.dumps({"weight_map": {
            "layer.weight": "model-00002.safetensors",
            "layer.bias": "model-00002.safetensors",
            "embedding.weight": "model-00001.safetensors",
        }}))
        first_shard = self.checkpoint / "model-00001.safetensors"
        second_shard = self.checkpoint / "model-00002.safetensors"
        first_shard.write_bytes(b"first shard")
        second_shard.write_bytes(b"second shard")

        self.assertEqual(
            export_model.checkpoint_files(self.checkpoint),
            [self.checkpoint / "config.json", index_file, first_shard, second_shard],
        )

    def test_missing_weight_shard_is_rejected(self):
        (self.checkpoint / "model.safetensors").unlink()
        (self.checkpoint / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {"layer.weight": "missing.safetensors"}})
        )
        with self.assertRaises(FileNotFoundError):
            export_model.checkpoint_files(self.checkpoint)


class SwinExportTest(unittest.TestCase):
    def test_export_matches_pytorch_on_same_pixels(self):
        import numpy as np
        import onnxruntime as ort
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
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "checkpoint"
            model.save_pretrained(checkpoint)
            processor.save_pretrained(checkpoint)
            output = export_model.export_model(checkpoint, Path(tmp) / "export")
            graph = output / "onnx-fp32" / "model.onnx"
            session = ort.InferenceSession(str(graph), providers=["CPUExecutionProvider"])
            pixels = processor(images=Image.fromarray(np.random.default_rng(42).integers(
                0, 256, size=(48, 40, 3), dtype=np.uint8,
            )), return_tensors="pt")["pixel_values"]
            with torch.no_grad():
                expected = model(pixel_values=pixels).logits.numpy()
            actual = session.run(["logits"], {"pixel_values": pixels.numpy()})[0]
            np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-5)
            self.assertEqual(json.loads((graph.parent / "config.json").read_text())["id2label"],
                             {"0": "Beta", "1": "Alpha", "2": "Gamma"})

            import browser_cam
            browser, head = browser_cam.prepare_browser_model(
                graph, checkpoint, Path(tmp) / "browser", pixels.numpy(),
            )
            np.testing.assert_array_equal(
                np.fromfile(head, dtype="<f4").reshape(model.classifier.weight.shape),
                model.classifier.weight.detach().numpy(),
            )
            result = browser_cam.run(browser, pixels.numpy())
            self.assertEqual(result["swin_layernorm"].shape, (1, 16, 16))
            np.testing.assert_allclose(result["logits"], expected, rtol=1e-2, atol=1e-3)


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
            with torch.no_grad():
                expected = model(pixel_values=pixels)
            logits, boxes = session.run(["logits", "pred_boxes"], {"pixel_values": pixels.numpy()})
            np.testing.assert_allclose(logits, expected.logits.numpy(), rtol=1e-4, atol=1e-5)
            np.testing.assert_allclose(boxes, expected.pred_boxes.numpy(), rtol=1e-4, atol=1e-5)


if __name__ == "__main__":
    unittest.main()

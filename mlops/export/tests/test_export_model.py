"""Export commands and offline Swin and detector exports."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import onnx
import onnxruntime as ort
import torch
from transformers import (
    RTDetrResNetConfig,
    RTDetrV2Config,
    RTDetrV2ForObjectDetection,
    SwinConfig,
    SwinForImageClassification,
)

sys.path.insert(0, str(Path(__file__).parents[1]))
import export_model  # noqa: E402


def save_tiny_swin(checkpoint):
    """Save a small random Swin classifier with three classes."""
    torch.manual_seed(42)
    model = SwinForImageClassification(SwinConfig(
        image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
        num_heads=[1, 2], window_size=2, num_labels=3,
    )).eval()
    model.save_pretrained(checkpoint)
    return model


def save_tiny_detector(checkpoint):
    """Save a small random RT-DETRv2 detector with one class."""
    torch.manual_seed(42)
    backbone = RTDetrResNetConfig(
        embedding_size=16, hidden_sizes=[16, 32, 64, 128],
        depths=[1, 1, 1, 1], layer_type="basic", out_indices=[2, 3, 4],
    )
    model = RTDetrV2ForObjectDetection(RTDetrV2Config(
        backbone_config=backbone, encoder_in_channels=[32, 64, 128],
        encoder_hidden_dim=32, encoder_ffn_dim=64, encoder_attention_heads=4,
        d_model=32, decoder_in_channels=[32, 32, 32], decoder_ffn_dim=64,
        decoder_attention_heads=4, decoder_layers=2, num_queries=10,
        num_denoising=0, num_labels=1, disable_custom_kernels=True,
    )).eval()
    model.save_pretrained(checkpoint)
    return model


class ExportCommandTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.checkpoint = Path(temp.name) / "checkpoint-1"
        self.checkpoint.mkdir()
        (self.checkpoint / "config.json").write_text(json.dumps({"model_type": "swin"}))
        self.output = Path(temp.name) / "export"

    def test_commands_use_local_files_and_published_opset(self):
        with patch.object(export_model.subprocess, "run") as run:
            export_model.export_model(self.checkpoint, self.output, quantize=True)
        export, quantize = (call.args[0] for call in run.call_args_list)
        self.assertEqual(export[export.index("--model") + 1], str(self.checkpoint))
        self.assertEqual(export[export.index("--task") + 1], "image-classification")
        self.assertEqual(export[export.index("--opset") + 1], "16")
        self.assertEqual(quantize[quantize.index("--onnx_model") + 1], str(self.output / "onnx-fp32"))
        for call in run.call_args_list:
            self.assertTrue(call.kwargs["check"])
            self.assertEqual(call.kwargs["env"]["HF_HUB_OFFLINE"], "1")

    def test_quantization_runs_only_when_requested(self):
        with patch.object(export_model.subprocess, "run") as run:
            export_model.export_model(self.checkpoint, self.output)
        self.assertEqual(run.call_count, 1)

    def test_existing_output_is_rejected_before_export(self):
        self.output.mkdir()
        with patch.object(export_model.subprocess, "run") as run:
            with self.assertRaises(FileExistsError):
                export_model.export_model(self.checkpoint, self.output)
        run.assert_not_called()

    def test_unknown_model_type_is_rejected(self):
        (self.checkpoint / "config.json").write_text(json.dumps({"model_type": "vit"}))
        with self.assertRaisesRegex(ValueError, "Unsupported model type: 'vit'"):
            export_model.export_model(self.checkpoint, self.output)


class SwinExportTest(unittest.TestCase):
    def test_fp32_matches_pytorch_and_int8_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = save_tiny_swin(root / "checkpoint")
            export_model.export_model(root / "checkpoint", root / "export", quantize=True)

            fp32 = root / "export/onnx-fp32/model.onnx"
            opsets = {opset.domain: opset.version for opset in onnx.load(fp32).opset_import}
            self.assertEqual(opsets[""], 16)
            pixels = torch.rand(2, 3, 32, 32)
            with torch.no_grad():
                expected = model(pixel_values=pixels).logits.numpy()
            session = ort.InferenceSession(str(fp32), providers=["CPUExecutionProvider"])
            logits, = session.run(["logits"], {"pixel_values": pixels.numpy()})
            np.testing.assert_allclose(logits, expected, rtol=1e-4, atol=1e-5)

            # INT8 is checked for a runnable model, not for FP32 accuracy.
            quantized = root / "export/onnx-quant/model_quantized.onnx"
            session = ort.InferenceSession(str(quantized), providers=["CPUExecutionProvider"])
            scores, = session.run(["logits"], {"pixel_values": pixels.numpy()})
            self.assertEqual(scores.shape, (2, 3))


class DetectorExportTest(unittest.TestCase):
    def test_logits_and_boxes_match_pytorch(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "checkpoint"
            model = save_tiny_detector(checkpoint)
            export_model.export_model(checkpoint, Path(tmp) / "export")
            session = ort.InferenceSession(str(Path(tmp) / "export/onnx-fp32/model.onnx"),
                                           providers=["CPUExecutionProvider"])
            pixels = torch.rand(2, 3, 64, 64)
            with torch.no_grad():
                expected = model(pixel_values=pixels)
            logits, boxes = session.run(["logits", "pred_boxes"], {"pixel_values": pixels.numpy()})
            np.testing.assert_allclose(logits, expected.logits.numpy(), rtol=1e-4, atol=1e-5)
            np.testing.assert_allclose(boxes, expected.pred_boxes.numpy(), rtol=1e-4, atol=1e-5)


if __name__ == "__main__":
    unittest.main()

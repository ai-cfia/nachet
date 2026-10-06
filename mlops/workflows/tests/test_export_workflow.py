"""Run the export workflow's commands with tiny checkpoints and local paths."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import onnxruntime as ort
import torch
import yaml

from mlops.export.tests.test_export_model import save_tiny_detector, save_tiny_swin


MLOPS = Path(__file__).resolve().parents[2]


class ExportWorkflowTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checkpoint = self.root / "runs/training/trainer-output/checkpoint-1"
        self.spec = yaml.safe_load(
            (MLOPS / "workflows/model-export-workflow-template.yaml").read_text()
        )["spec"]
        self.templates = {item["name"]: item for item in self.spec["templates"]}
        torch.set_num_threads(1)
        torch.manual_seed(42)

    def run_step(self, name, quantize):
        container = self.templates[name]["container"]
        command = [*container["command"], *container["args"]]
        replacements = {
            "/runs/": str(self.root / "runs") + "/",
            "/exports/": str(self.root / "exports") + "/",
            "{{inputs.parameters.training-run}}": "training",
            "{{inputs.parameters.checkpoint}}": "checkpoint-1",
            "{{inputs.parameters.quantize}}": str(quantize).lower(),
            "{{workflow.name}}": "export-int8" if quantize else "export-fp32",
        }
        for old, new in replacements.items():
            command = [argument.replace(old, new) for argument in command]
        env = dict(os.environ, HF_HUB_OFFLINE="1")
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
        process = subprocess.run(
            command, cwd=MLOPS / "export", env=env,
            capture_output=True, text=True, timeout=240,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def check_export(self, model, pixels, quantize):
        original = hashlib.sha256((self.checkpoint / "model.safetensors").read_bytes()).digest()
        self.run_step("export", quantize)
        output = self.root / "exports" / ("export-int8" if quantize else "export-fp32")
        session = ort.InferenceSession(
            str(output / "onnx-fp32/model.onnx"), providers=["CPUExecutionProvider"],
        )
        names = [item.name for item in session.get_outputs()]
        actual = dict(zip(names, session.run(None, {"pixel_values": pixels.numpy()})))
        with torch.no_grad():
            expected = model(pixel_values=pixels)
        for name in names:
            np.testing.assert_allclose(actual[name], getattr(expected, name).numpy(),
                                       rtol=1e-4, atol=1e-5)
        quantized = output / "onnx-quant/model_quantized.onnx"
        self.assertEqual(quantized.exists(), quantize)
        if quantize:
            session = ort.InferenceSession(str(quantized), providers=["CPUExecutionProvider"])
            scores, = session.run(["logits"], {"pixel_values": pixels.numpy()})
            self.assertEqual(scores.shape, actual["logits"].shape)
        self.assertEqual(
            hashlib.sha256((self.checkpoint / "model.safetensors").read_bytes()).digest(),
            original,
        )
        return output

    def test_classifier_export_and_browser_preparation_use_the_selected_checkpoint(self):
        model = save_tiny_swin(self.checkpoint)
        pixels = torch.rand(1, 3, 32, 32)
        step = self.templates["export-model"]["steps"][1][0]
        self.assertEqual(step["when"], "{{=inputs.parameters['model-kind'] == 'classifier'}}")
        for quantize in (False, True):
            with self.subTest(quantize=quantize):
                output = self.check_export(model, pixels, quantize)
                self.run_step("prepare-browser", quantize)
                session = ort.InferenceSession(
                    str(output / "browser/model_browser.fp16.onnx"),
                    providers=["CPUExecutionProvider"],
                )
                logits, features = session.run(
                    ["logits", "swin_layernorm"], {"pixel_values": pixels.numpy()},
                )
                self.assertEqual(logits.shape, (1, 3))
                self.assertEqual(features.shape[-1], model.classifier.in_features)
                head = output / "browser/classifier_head_3spp.f32.bin"
                self.assertEqual(head.read_bytes(),
                                 model.classifier.weight.detach().numpy().astype("<f4").tobytes())

    def test_detector_export_uses_the_selected_checkpoint(self):
        model = save_tiny_detector(self.checkpoint)
        pixels = torch.rand(1, 3, 64, 64)
        for quantize in (False, True):
            with self.subTest(quantize=quantize):
                output = self.check_export(model, pixels, quantize)
                self.assertFalse((output / "browser").exists())


if __name__ == "__main__":
    unittest.main()

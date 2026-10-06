"""Browser CAM preparation from a real, tiny Swin export."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parents[1]))
import browser_cam  # noqa: E402
import export_model  # noqa: E402
from test_export_model import save_tiny_swin  # noqa: E402


class BrowserCamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.checkpoint = cls.root / "checkpoint"
        cls.model = save_tiny_swin(cls.checkpoint)
        export_model.export_model(cls.checkpoint, cls.root / "export")
        cls.source = cls.root / "export/onnx-fp32/model.onnx"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_browser_files_match_mini_cam_contract(self):
        browser, head = browser_cam.prepare_browser_model(
            self.source, self.checkpoint, self.root / "browser",
        )
        weight = self.model.classifier.weight.detach().numpy()
        bias = self.model.classifier.bias.detach().numpy()
        self.assertEqual(head.name, "classifier_head_3spp.f32.bin")
        self.assertEqual(head.read_bytes(), weight.astype("<f4").tobytes())

        pixels = torch.rand(2, 3, 32, 32)
        with torch.no_grad():
            expected = self.model(pixel_values=pixels).logits.numpy()
        outputs = browser_cam.run(browser, pixels.numpy())
        features = outputs[browser_cam.FEATURE_OUTPUT_NAME]
        self.assertEqual(outputs["logits"].dtype, np.float32)
        self.assertEqual(features.dtype, np.float32)
        self.assertEqual(features.shape, (2, 16, 16))
        np.testing.assert_allclose(outputs["logits"], expected, atol=1e-2)
        # Mini's CAM relies on each logit being the token average of features · W plus b.
        np.testing.assert_allclose(features.mean(axis=1) @ weight.T + bias, outputs["logits"], atol=1e-2)

    def test_newer_opset_export_is_rejected(self):
        output = self.root / "export-opset-18"
        with patch.object(export_model, "OPSET", "18"):
            export_model.export_model(self.checkpoint, output)
        with self.assertRaisesRegex(ValueError, "export it with export_model.py"):
            browser_cam.add_feature_output(output / "onnx-fp32/model.onnx", self.root / "unused.onnx")


if __name__ == "__main__":
    unittest.main()

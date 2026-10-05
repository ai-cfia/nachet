"""Release file selection and Hub PR creation, with uploads mocked."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import ModelRelease  # noqa: E402


class ModelReleaseTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checkpoint = self.root / "checkpoint-42"
        self.exports = self.root / "exports"
        self.output = self.root / "release"
        self.checkpoint.mkdir()
        (self.checkpoint / "config.json").write_text(json.dumps({
            "model_type": "swin", "id2label": {"0": "seed", "1": "other"},
        }))
        (self.checkpoint / "model.safetensors").write_bytes(b"selected weights")
        (self.checkpoint / "preprocessor_config.json").write_text('{"size": 384}\n')
        (self.checkpoint / "optimizer.pt").write_bytes(b"training state")
        (self.checkpoint / ".env").write_text("fixture, not a credential\n")
        for name in ("onnx-fp32", "onnx-quant", "browser"):
            (self.exports / name).mkdir(parents=True)
        (self.exports / "onnx-fp32/model.onnx").write_bytes(b"evaluated FP32")
        (self.exports / "onnx-quant/model_quantized.onnx").write_bytes(b"evaluated INT8")
        (self.exports / "browser/model_browser.fp16.onnx").write_bytes(b"evaluated FP16")
        (self.exports / "browser/classifier_head_2spp.f32.bin").write_bytes(b"head weights")
        (self.exports / "browser/model.opt.onnx").write_bytes(b"intermediate graph")
        self.card = self.root / "card.md"
        self.card.write_text("---\nlibrary_name: transformers\n---\n# Reviewed model\n")
        self.report = self.root / "converted-metrics.json"
        self.report.write_text('{"fixture_only": true}\n')
        environment = patch.dict(os.environ, {"HF_TOKEN": "offline-test-token"})
        environment.start()
        self.addCleanup(environment.stop)
        api = patch.object(ModelRelease, "HfApi")
        self.api = api.start()
        self.addCleanup(api.stop)
        self.api.return_value.upload_folder.return_value.pr_url = "mock-hub-pr"

    def test_fp32_and_int8_files_are_copied_without_training_state(self):
        ModelRelease.release_model(
            self.checkpoint, self.exports, self.card, self.output, "example/model",
            evaluation=[self.report], include_int8=True,
        )
        expected = {
            "config.json", "model.safetensors", "preprocessor_config.json", "README.md",
            "onnx/model.onnx", "onnx/model_quantized.onnx", "evaluation/converted-metrics.json",
        }
        actual = {path.relative_to(self.output).as_posix()
                  for path in self.output.rglob("*") if path.is_file()}
        self.assertEqual(actual, expected)
        self.assertEqual((self.output / "onnx/model.onnx").read_bytes(),
                         (self.exports / "onnx-fp32/model.onnx").read_bytes())
        self.assertEqual((self.output / "onnx/model_quantized.onnx").read_bytes(),
                         (self.exports / "onnx-quant/model_quantized.onnx").read_bytes())

    def test_browser_release_uses_mini_paths_and_can_also_include_int8(self):
        ModelRelease.release_model(
            self.checkpoint, self.exports, self.card, self.output, "example/model",
            browser=True, include_int8=True,
        )
        self.assertEqual((self.output / "onnx/model.onnx").read_bytes(),
                         (self.exports / "browser/model_browser.fp16.onnx").read_bytes())
        self.assertEqual((self.output / "classifier_head_2spp.f32.bin").read_bytes(),
                         (self.exports / "browser/classifier_head_2spp.f32.bin").read_bytes())
        self.assertEqual((self.output / "onnx/model_quantized.onnx").read_bytes(),
                         (self.exports / "onnx-quant/model_quantized.onnx").read_bytes())
        self.assertFalse((self.output / "evaluation").exists())

    def test_cli_creates_a_hub_pr_for_a_detector_without_reports(self):
        (self.checkpoint / "config.json").write_text('{"model_type": "rt_detr_v2"}\n')
        self.card.write_text("---\npipeline_tag: object-detection\n---\n# Reviewed detector\n")
        args = ["ModelRelease.py", "--checkpoint", str(self.checkpoint),
                "--exports", str(self.exports), "--model-card", str(self.card),
                "--output", str(self.output), "--repo-id", "example/model"]
        with patch.object(sys, "argv", args):
            ModelRelease.main()
        self.api.assert_called_once_with(endpoint="https://huggingface.co", token="offline-test-token")
        self.api.return_value.create_repo.assert_called_once_with(
            repo_id="example/model", repo_type="model", private=False, exist_ok=True,
        )
        self.api.return_value.upload_folder.assert_called_once_with(
            folder_path=str(self.output), repo_id="example/model", repo_type="model",
            create_pr=True, commit_message="Publish checkpoint-42",
        )
        self.assertEqual(list(self.output.glob("classifier_head*")), [])

    def test_duplicate_report_names_do_not_overwrite_evaluation(self):
        second = self.root / "another-evaluation"
        second.mkdir()
        report = second / self.report.name
        report.write_text('{"different_report": true}\n')
        with self.assertRaisesRegex(ValueError, "distinct filenames"):
            ModelRelease.release_model(
                self.checkpoint, self.exports, self.card, self.output, "example/model",
                evaluation=[self.report, report],
            )
        self.assertFalse(self.output.exists())
        self.api.assert_not_called()


if __name__ == "__main__":
    unittest.main()

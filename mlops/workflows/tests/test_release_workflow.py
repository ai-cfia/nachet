"""Exercise release commands locally; mock only the final Hub upload."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mlflow import MlflowClient
from PIL import Image
import torch
from transformers import RTDetrImageProcessor, ViTImageProcessor
import yaml

from mlops.export import ModelRelease
from mlops.export.tests.test_export_model import save_tiny_detector, save_tiny_swin
from mlops.training.checkpoints import REQUIRED_CHECKPOINT_FILES


MLOPS = Path(__file__).resolve().parents[2]


class ReleaseWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.templates = {item["name"]: item for item in yaml.safe_load(
            (MLOPS / "workflows/model-release-workflow-template.yaml").read_text(),
        )["spec"]["templates"]}
        self.export_templates = {item["name"]: item for item in yaml.safe_load(
            (MLOPS / "workflows/model-export-workflow-template.yaml").read_text(),
        )["spec"]["templates"]}
        torch.set_num_threads(1)
        torch.manual_seed(42)

    def run_container(self, template, parameters, cwd, extra_env=None, capture_command=False):
        container = template["container"]
        replacements = {
            "{{workflow.name}}": "release-smoke",
            "/runs/": str(self.root / "runs") + "/",
            "/inputs/": str(self.root / "inputs") + "/",
            "/exports/": str(self.root / "exports") + "/",
            "/tmp/": str(self.root / "tmp") + "/",
            "/scratch/": str(self.root / "scratch") + "/",
            "{{=toJson({'enum': jsonpath(inputs.parameters.checkpoints, '$')})}}":
                json.dumps({"enum": json.loads(parameters["checkpoints"])}),
            "{{=inputs.parameters['model-kind'] == 'classifier' ? "
            "'validation_metrics.json' : 'detection_metrics.json'}}":
                "validation_metrics.json" if parameters["model-kind"] == "classifier"
                else "detection_metrics.json",
        }
        replacements.update({"{{inputs.parameters." + key + "}}": value
                             for key, value in parameters.items()})

        def render(value):
            if value in {"/runs", "/inputs", "/exports", "/tmp", "/scratch"}:
                return str(self.root / value.lstrip("/"))
            for old, new in replacements.items():
                value = value.replace(old, new)
            self.assertNotIn("{{", value)
            return value

        command = [render(arg) for arg in [*container["command"], *container["args"]]]
        if capture_command:
            # Run the shell's argument construction, then invoke Python with the Hub mocked.
            self.assertIn('exec "$@"', command[2])
            command[2] = command[2].replace('exec "$@"', "printf '%s\\0' \"$@\"")
        env = dict(os.environ, HF_HUB_OFFLINE="1", ORT_DISABLE_TELEMETRY="1")
        for setting in container.get("env", []):
            if "value" in setting:
                env[setting["name"]] = render(setting["value"])
        env.update(extra_env or {})
        cwd = render(container["workingDir"]) if "workingDir" in container else cwd
        process = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=240)
        self.assertEqual(process.returncode, 0, process.stdout.decode() + process.stderr.decode())
        return process.stdout

    def test_selected_artifacts_are_evaluated_in_mlflow_then_packaged(self):
        for kind in ("classifier", "detector"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary)
                self.check_release(kind)

    def check_release(self, kind):
        inputs = self.root / "inputs"
        inputs.mkdir()
        (self.root / "tmp").mkdir()
        checkpoint = self.root / "runs/training/trainer-output/checkpoint-1"
        if kind == "classifier":
            model = save_tiny_swin(checkpoint)
            processor = ViTImageProcessor(size={"height": 32, "width": 32})
            for label in model.config.id2label.values():
                folder = inputs / "external" / label
                folder.mkdir(parents=True)
                Image.new("RGB", (40, 40), "red").save(folder / "seed.png")
            external = "external"
            metrics_name = "validation_metrics.json"
        else:
            save_tiny_detector(checkpoint)
            processor = RTDetrImageProcessor(
                size={"max_height": 64, "max_width": 64},
                do_pad=True, pad_size={"height": 64, "width": 64},
            )
            Image.new("RGB", (80, 40), "red").save(inputs / "seed.png")
            (inputs / "annotations.json").write_text(json.dumps({
                "images": [{"id": 1, "file_name": "seed.png", "width": 80, "height": 40}],
                "categories": [{"id": 1, "name": "Species A"}],
                "annotations": [{"id": 1, "image_id": 1, "category_id": 1,
                                 "bbox": [4, 4, 16, 12], "area": 192, "iscrowd": 0}],
            }))
            external = "external.json"
            (inputs / external).write_text(json.dumps({"sources": [
                {"json_path": "annotations.json", "images_dir": "."},
            ]}))
            metrics_name = "detection_metrics.json"
        processor.save_pretrained(checkpoint)
        for name in REQUIRED_CHECKPOINT_FILES:
            (checkpoint / name).touch()
        card = inputs / "card.md"
        card.write_text("# Reviewed fixture card\n")
        client = MlflowClient(tracking_uri=(self.root / "mlruns").as_uri())
        experiment = client.create_experiment(
            "release-smoke", artifact_location=(self.root / "artifacts").as_uri(),
        )
        parent = client.create_run(experiment)
        client.set_terminated(parent.info.run_id)
        parameters = {
            "model-kind": kind, "training-run": "training", "checkpoint": "checkpoint-1",
            "checkpoints": '["checkpoint-1"]',
            "quantize": "true", "device": "cpu", "validation-input": external,
            "mlflow-run-id": parent.info.run_id,
        }
        export_python = Path(os.environ.get("NACHET_EXPORT_PYTHON", sys.executable))
        export_env = {"PATH": str(export_python.parent) + os.pathsep + os.environ["PATH"]}
        self.run_container(self.templates["check-selection"], parameters,
                           MLOPS / "training", export_env)
        self.run_container(self.export_templates["export"], parameters, MLOPS / "export", export_env)
        if kind == "classifier":
            self.run_container(self.export_templates["prepare-browser"], parameters,
                               MLOPS / "export", export_env)

        evaluation_env = {
            "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": os.pathsep.join([
                str(MLOPS / "training" / kind / "src"), str(MLOPS / "training"),
            ]),
            "MLFLOW_TRACKING_URI": (self.root / "mlruns").as_uri(),
        }
        exports = self.root / "exports/release-smoke"
        flow = self.templates["release-model"]["steps"]

        def step_parameters(step):
            values = dict(parameters)
            for item in step["arguments"]["parameters"]:
                value = item["value"]
                for key, replacement in parameters.items():
                    value = value.replace("{{inputs.parameters." + key + "}}", replacement)
                for key, replacement in {"repo-id": "example/release", "model-card": "card.md",
                                         "browser-repo-id": "example/cam",
                                         "browser-model-card": "card.md"}.items():
                    value = value.replace(
                        "{{steps.review-publication.outputs.parameters." + key + "}}", replacement,
                    )
                values[item["name"]] = value
            return values

        for group in flow:
            step = group[0]
            if step.get("template") != "evaluate-converted":
                continue
            if kind == "detector" and step["name"] == "evaluate-browser":
                continue
            values = step_parameters(step)
            result = json.loads(self.run_container(
                self.templates["evaluate-converted"], values, inputs, evaluation_env,
            ))
            child = client.get_run(result["mlflow_run_id"])
            self.assertEqual(child.info.status, "FINISHED")
            self.assertEqual(child.data.tags["mlflow.parentRunId"], parent.info.run_id)
            report = exports / "evaluation" / values["variant"] / "reports" / metrics_name
            metadata = json.loads(report.read_text())["onnx_model"]
            artifact = exports / values["onnx-file"]
            self.assertEqual(metadata["sha256"], hashlib.sha256(artifact.read_bytes()).hexdigest())
            downloaded = Path(client.download_artifacts(child.info.run_id, "evaluation/" + metrics_name))
            self.assertEqual(downloaded.read_bytes(), report.read_bytes())

        for browser in (False, True) if kind == "classifier" else (False,):
            shutil.rmtree(self.root / "tmp")
            (self.root / "tmp").mkdir()
            step_name = "publish-browser" if browser else "publish-fp32"
            step = next(group[0] for group in flow if group[0]["name"] == step_name)
            values = step_parameters(step)
            command = self.run_container(
                self.templates["publish"], values, MLOPS / "export", capture_command=True,
            ).decode().rstrip("\0").split("\0")
            with patch.dict(os.environ, {"HF_TOKEN": "offline-test-token"}), \
                    patch.object(ModelRelease, "HfApi") as api, \
                    patch.object(sys, "argv", command[1:]):
                api.return_value.upload_folder.return_value.pr_url = "mock-hub-pr"
                ModelRelease.main()
            api.return_value.upload_folder.assert_called_once()
            self.assertTrue(api.return_value.upload_folder.call_args.kwargs["create_pr"])
            model_file = exports / ("browser/model_browser.fp16.onnx" if browser
                                    else "onnx-fp32/model.onnx")
            self.assertEqual((self.root / "tmp/release/onnx/model.onnx").read_bytes(),
                             model_file.read_bytes())

    def test_human_gates_and_token_are_kept_at_their_boundaries(self):
        selected = self.templates["release-selected"]["steps"]
        self.assertIn("!= 'none'", selected[-1][0]["when"])
        release = self.templates["release-model"]["steps"]
        approval = next(index for index, group in enumerate(release)
                        if group[0].get("template") == "publication-review")
        for index, group in enumerate(release):
            step = group[0]
            if step.get("template") == "evaluate-converted":
                self.assertLess(index, approval)
            if step.get("template") == "publish":
                self.assertGreater(index, approval)
                self.assertIn("outputs.parameters.approve == 'yes'", step["when"])
        for name, template in self.templates.items():
            env = template.get("container", {}).get("env", [])
            has_token = any(setting["name"] == "HF_TOKEN" for setting in env)
            self.assertEqual(has_token, name == "publish")


if __name__ == "__main__":
    unittest.main()

"""Run the workflow evaluation commands against tiny checkpoints and local MLflow."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mlflow import MlflowClient
from PIL import Image
import torch
from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor
import yaml


MLOPS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MLOPS / "training/detector/tests"))
import test_detector_evaluation  # noqa: E402
sys.path.pop(0)


class EvaluationWorkflowTests(unittest.TestCase):
    def test_selected_checkpoint_reports_reach_mlflow(self):
        torch.set_num_threads(1)
        torch.manual_seed(2438)
        for kind in ("classifier", "detector"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                self.check_workflow(kind, Path(temporary))

    def check_workflow(self, kind, root):
        spec = yaml.safe_load((MLOPS / "workflows" / f"{kind}-training-workflow-template.yaml").read_text())["spec"]
        templates = {item["name"]: item for item in spec["templates"]}
        step = templates[f"{kind}-training"]["steps"][-1][0]
        parameter = "external-validation-dir" if kind == "classifier" else "external-validation-config"
        defaults = {item["name"]: item["value"] for item in spec["arguments"]["parameters"]}
        self.assertEqual(defaults[parameter], "none")
        self.assertEqual(step["when"], "{{=workflow.parameters['" + parameter + "'] != 'none'}}")
        self.assertEqual(step["withParam"], "{{steps.check-checkpoint-selections.outputs.parameters.selected-checkpoints}}")
        container = templates[step["template"]]["container"]
        self.assertTrue(next(m for m in container["volumeMounts"] if m["mountPath"] == "/inputs")["readOnly"])

        inputs = root / "inputs"
        inputs.mkdir()
        checkpoint = root / "runs/smoke/trainer-output/checkpoint-1"
        if kind == "classifier":
            model = SwinForImageClassification(SwinConfig(
                image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
                num_heads=[1, 2], window_size=4, num_labels=2,
                id2label={0: "Alpha", 1: "Beta"}, label2id={"Alpha": 0, "Beta": 1},
            ))
            processor = ViTImageProcessor(size={"height": 32, "width": 32})
            for label in ("Alpha", "Beta"):
                folder = inputs / "external" / label
                folder.mkdir(parents=True)
                Image.new("RGB", (40, 40), "red").save(folder / "seed.png")
            external = "external"
        else:
            model = test_detector_evaluation.DetectorEvaluationTest().model()
            model.config.id2label = {0: "seed"}
            model.config.label2id = {"seed": 0}
            from transformers import RTDetrImageProcessor
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
        model.save_pretrained(checkpoint)
        processor.save_pretrained(checkpoint)
        weights = hashlib.sha256((checkpoint / "model.safetensors").read_bytes()).hexdigest()

        client = MlflowClient(tracking_uri=(root / "mlruns").as_uri())
        experiment = client.create_experiment("smoke", artifact_location=(root / "artifacts").as_uri())
        parent = client.create_run(experiment)
        client.set_terminated(parent.info.run_id)
        # Substitute only cluster paths and run IDs; execute the YAML's actual arguments.
        replacements = {
            "{{inputs.parameters.mlflow-run-id}}": parent.info.run_id,
            "{{inputs.parameters.checkpoint}}": "checkpoint-1",
            "{{workflow.name}}": "smoke",
            "{{workflow.parameters." + parameter + "}}": external,
            "/runs/": str(root / "runs") + "/",
            "/inputs/": str(inputs) + "/",
        }
        command = [*container["command"], *container["args"]]
        command[0] = sys.executable
        for old, new in replacements.items():
            command = [arg.replace(old, new) for arg in command]
        self.assertNotIn("{{", " ".join(command))
        env = dict(os.environ, MLFLOW_TRACKING_URI=(root / "mlruns").as_uri())
        env["PYTHONPATH"] = os.pathsep.join([
            str(MLOPS / "training" / kind / "src"), str(MLOPS / "training"),
            os.environ.get("PYTHONPATH", ""),
        ])
        process = subprocess.run(command, cwd=inputs, env=env, capture_output=True, text=True, timeout=240)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["checkpoint"], "checkpoint-1")
        child = client.get_run(result["mlflow_run_id"])
        self.assertEqual(child.info.status, "FINISHED")
        self.assertEqual(child.data.tags["mlflow.parentRunId"], parent.info.run_id)
        self.assertEqual(client.get_run(parent.info.run_id).info.status, "FINISHED")
        reports = root / "runs/smoke/evaluation/checkpoint-1/reports"
        files = [path for path in reports.rglob("*") if path.is_file()]
        self.assertTrue(any(path.suffix == ".png" for path in files))
        self.assertTrue(any(path.suffix == ".json" for path in files))
        if kind == "classifier":
            self.assertEqual(len(files), 8)
        for path in files:
            artifact = "evaluation/" + path.relative_to(reports).as_posix()
            downloaded = Path(client.download_artifacts(child.info.run_id, artifact))
            self.assertEqual(downloaded.read_bytes(), path.read_bytes())
        self.assertEqual(hashlib.sha256((checkpoint / "model.safetensors").read_bytes()).hexdigest(), weights)


if __name__ == "__main__":
    unittest.main()

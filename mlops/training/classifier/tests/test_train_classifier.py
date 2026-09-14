import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import torch
from mlflow import MlflowClient
from PIL import Image
from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor


SCRIPT = Path(__file__).parents[1] / "src" / "train_classifier.py"


class ClassifierTrainingTest(unittest.TestCase):
    def test_train_evaluate_and_resume_from_a_real_checkpoint(self):
        for separate_validation in (False, True):
            with self.subTest(separate_validation=separate_validation):
                self.check_training_and_resume(separate_validation)

    def check_training_and_resume(self, separate_validation):
        # Tiny local weights and labelled images exercise the real Trainer offline.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_path = root / "model"
            torch.manual_seed(42)
            model = SwinForImageClassification(
                SwinConfig(
                    image_size=32,
                    patch_size=4,
                    embed_dim=8,
                    depths=[1, 1],
                    num_heads=[1, 2],
                    window_size=4,
                    num_labels=2,
                )
            )
            model.save_pretrained(model_path)
            ViTImageProcessor(size={"height": 32, "width": 32}).save_pretrained(
                model_path
            )
            for split, count in (("Training", 2), ("Validation", 1)):
                for label, color in (("a", "red"), ("b", "blue")):
                    directory = root / split / label
                    directory.mkdir(parents=True)
                    for index in range(count):
                        Image.new("RGB", (40, 40), color).save(
                            directory / f"{index}.png"
                        )
            output = root / "runs" / "test-run" / "trainer-output"
            environment = {
                **os.environ,
                "HF_HUB_OFFLINE": "1",
                "HF_DATASETS_OFFLINE": "1",
                "HF_HOME": str(root / "hf"),
                "OMP_NUM_THREADS": "1",
                "MLFLOW_TRACKING_URI": (root / "mlruns").as_uri(),
                "MLFLOW_EXPERIMENT_NAME": "classifier-test",
                "MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING": "false",
            }
            client = MlflowClient(tracking_uri=environment["MLFLOW_TRACKING_URI"])
            experiment = client.create_experiment("classifier-test")
            run_id = client.create_run(experiment).info.run_id
            environment["MLFLOW_RUN_ID"] = run_id
            # Exercise the migrated script without depending on the runtime launcher.
            command = [
                sys.executable, str(SCRIPT),
                "--model_name_or_path", str(model_path),
                "--train_dir", str(root / "Training"),
                "--output_dir", str(output),
                "--do_train", "--do_eval", "--use_cpu",
                "--num_train_epochs", "2",
                "--per_device_train_batch_size", "2",
                "--per_device_eval_batch_size", "3",
                "--max_train_samples", "32",
                "--max_eval_samples", "16",
                "--save_strategy", "epoch",
                "--eval_strategy", "epoch",
                "--report_to", "mlflow",
                "--disable_tqdm", "true",
                "--seed", "2438",
            ]
            if separate_validation:
                command.extend(["--validation_dir", str(root / "Validation")])
            # Interrupt just after a real checkpoint save, without changing run settings.
            interrupted_training = """
import sys
sys.path.insert(0, sys.argv.pop(1))
import train_classifier
import numpy as np
from types import SimpleNamespace
from transformers import TrainerCallback

class InterruptAfterSave(TrainerCallback):
    def on_save(self, args, state, control, **kwargs):
        raise RuntimeError("test interruption after checkpoint")

original_init = train_classifier.BalancedTrainer.__init__
def init_with_interruption(self, *args, **kwargs):
    # Known predictions verify the local metric values independently of model quality.
    result = kwargs['compute_metrics'](SimpleNamespace(
        predictions=np.array([[1, 0], [1, 0], [0, 1], [0, 1]]),
        label_ids=np.array([0, 1, 1, 1]),
    ))
    for name, expected in dict(accuracy=.75, precision=.75, recall=5/6, f1=11/15).items():
        assert np.isclose(result[name], expected), (name, result[name], expected)
    original_init(self, *args, **kwargs)
    self.add_callback(InterruptAfterSave())

train_classifier.BalancedTrainer.__init__ = init_with_interruption
train_classifier.main()
"""
            first = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    interrupted_training,
                    str(SCRIPT.parent),
                    *command[2:],
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(first.returncode, 0)
            self.assertIn("test interruption after checkpoint", first.stderr)
            checkpoints = sorted(output.glob("checkpoint-*"))
            self.assertTrue(checkpoints)
            self.assertTrue((checkpoints[-1] / "optimizer.pt").is_file())
            # The same invocation discovers the checkpoint and finishes the interrupted run.
            second = subprocess.run(
                command,
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertTrue((output / "eval_results.json").is_file())
            latest_step = max(
                int(p.name.split("-")[1]) for p in output.glob("checkpoint-*")
            )
            previous_step = max(int(p.name.split("-")[1]) for p in checkpoints)
            self.assertGreater(latest_step, previous_step)
            self.assertEqual(len(client.search_runs([experiment])), 1)
            run = client.get_run(run_id)
            self.assertIn("eval_accuracy", run.data.metrics)
            self.assertEqual(
                run.data.params["train_val_split"],
                "None" if separate_validation else "0.15",
            )


if __name__ == "__main__":
    unittest.main()

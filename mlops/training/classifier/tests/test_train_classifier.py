import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import torch
from mlflow import MlflowClient
from PIL import Image
from safetensors.torch import load_file, save_file
from transformers import SwinConfig, SwinForImageClassification, TrainingArguments, ViTImageProcessor


SCRIPT = Path(__file__).parents[1] / "src" / "train_classifier.py"


class ClassifierTrainingTest(unittest.TestCase):
    def test_checkpoint_restores_every_weight(self):
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            from train_classifier import BalancedTrainer
        finally:
            sys.path.pop(0)
        # Different initial weights expose a partial restore even when training runs.
        config = SwinConfig(
            image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
            num_heads=[1, 2], window_size=4, num_labels=2,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = SwinForImageClassification(config)
            with torch.no_grad():
                for parameter in source.parameters():
                    parameter.fill_(0.125)
            for legacy_keys in (True, False):
                with self.subTest(legacy_keys=legacy_keys):
                    checkpoint = root / "checkpoint-1"
                    source.save_pretrained(checkpoint, save_original_format=legacy_keys)
                    model = SwinForImageClassification(config)
                    trainer = BalancedTrainer(model=model, args=TrainingArguments(
                        output_dir=str(root / "output"), use_cpu=True, report_to="none",
                    ))
                    trainer.create_optimizer()
                    parameters = list(model.parameters())
                    trainer._load_from_checkpoint(str(checkpoint))
                    for name, expected in source.state_dict().items():
                        torch.testing.assert_close(model.state_dict()[name], expected, rtol=0, atol=0)
                    self.assertTrue(all(a is b for a, b in zip(parameters, model.parameters())))
                    with torch.no_grad():
                        for parameter in model.parameters():
                            parameter.fill_(-0.25)
                    trainer.state.best_model_checkpoint = str(checkpoint)
                    trainer._load_best_model()
                    for name, expected in source.state_dict().items():
                        torch.testing.assert_close(model.state_dict()[name], expected, rtol=0, atol=0)

            # A loader may initialize a missing weight; reject that before mutation.
            weights_file = checkpoint / "model.safetensors"
            weights = load_file(weights_file)
            del weights["classifier.bias"]
            save_file(weights, weights_file)
            before = {name: value.clone() for name, value in model.state_dict().items()}
            with self.assertRaisesRegex(ValueError, "could not be fully restored"):
                trainer._load_from_checkpoint(str(checkpoint))
            for name, expected in before.items():
                torch.testing.assert_close(model.state_dict()[name], expected, rtol=0, atol=0)

    def test_train_evaluate_and_resume_from_a_real_checkpoint(self):
        for separate_validation in (False, True):
            with self.subTest(separate_validation=separate_validation):
                self.check_training_and_resume(separate_validation)

    def test_resume_into_another_output_directory(self):
        self.check_training_and_resume(True, new_output=True)

    def check_training_and_resume(self, separate_validation, new_output=False):
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
                "HF_MLFLOW_LOG_ARTIFACTS": "TRUE",
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
import os
import torch
from pathlib import Path
from types import SimpleNamespace
from transformers import TrainerCallback

class InterruptAfterSave(TrainerCallback):
    def on_train_begin(self, args, state, control, model=None, **kwargs):
        if "EXPECTED_WEIGHTS" in os.environ:
            expected = torch.load(os.environ["EXPECTED_WEIGHTS"], weights_only=True)
            for name, value in model.state_dict().items():
                torch.testing.assert_close(value, expected[name], rtol=0, atol=0)

    def on_save(self, args, state, control, **kwargs):
        if "EXPECTED_WEIGHTS" not in os.environ:
            torch.save(kwargs["model"].state_dict(), Path(args.output_dir).parent / "expected-weights.pt")
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
            if new_output:
                output = root / "runs" / "resumed-run" / "trainer-output"
                command[command.index("--output_dir") + 1] = str(output)
            # The launcher passes an explicit checkpoint even for same-directory retries.
            command.extend(["--resume_from_checkpoint", str(checkpoints[-1])])
            environment["EXPECTED_WEIGHTS"] = str(
                root / "runs" / "test-run" / "expected-weights.pt"
            )
            second = subprocess.run(
                [sys.executable, "-c", interrupted_training, str(SCRIPT.parent), *command[2:]],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertNotIn("Changing param values is not allowed", second.stdout + second.stderr)
            self.assertTrue((output / "eval_results.json").is_file())
            latest_step = max(
                int(p.name.split("-")[1]) for p in output.glob("checkpoint-*")
            )
            previous_step = max(int(p.name.split("-")[1]) for p in checkpoints)
            self.assertGreater(latest_step, previous_step)
            runs = client.search_runs([experiment])
            self.assertEqual(len(runs), 3)
            attempts = [run for run in runs if run.data.tags.get("mlflow.parentRunId") == run_id]
            self.assertEqual(len(attempts), 2)
            self.assertEqual({run.info.status for run in attempts}, {"FAILED", "FINISHED"})
            run = next(run for run in attempts if run.info.status == "FINISHED")
            self.assertEqual(run.data.params["output_dir"], str(output))
            self.assertEqual(run.data.params["resume_from_checkpoint"], str(checkpoints[-1]))
            self.assertIn("eval_accuracy", run.data.metrics)
            self.assertEqual(
                run.data.params["train_val_split"],
                "None" if separate_validation else "0.15",
            )


if __name__ == "__main__":
    unittest.main()

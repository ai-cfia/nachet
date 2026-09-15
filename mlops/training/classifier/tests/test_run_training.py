import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "run_training.py"


class ClassifierCommandTest(unittest.TestCase):
    def test_smoke_inputs_overrides_and_resume(self):
        # A prepared image folder enters the launcher, not a detector COCO config.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("Training", "Validation", "model"):
                (root / name).mkdir()
            source = root / "runs" / "previous"
            checkpoint = source / "trainer-output" / "checkpoint-2"
            checkpoint.mkdir(parents=True)
            for name in (
                "model.safetensors",
                "optimizer.pt",
                "scheduler.pt",
                "rng_state.pth",
                "trainer_state.json",
                "training_args.bin",
            ):
                (checkpoint / name).touch()
            (source / "mlflow-run-id").write_text("existing-run\n")
            arguments = [
                sys.executable,
                str(SCRIPT),
                "--dataset-root",
                str(root),
                "--train-dir",
                "Training",
                "--validation-dir",
                "Validation",
                "--model-path",
                "model",
                "--run-profile",
                "smoke",
                "--run-id",
                "new",
                "--runs-root",
                str(root / "runs"),
                "--resume-run-id",
                "previous",
                "--batch-size",
                "3",
                "--dry-run",
            ]
            result = subprocess.run(arguments, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            command = shlex.split(result.stdout)
            for flag, value in {
                "--train_dir": str(root / "Training"),
                "--validation_dir": str(root / "Validation"),
                "--num_train_epochs": "1",
                "--per_device_train_batch_size": "3",
                "--resume_from_checkpoint": str(checkpoint),
            }.items():
                self.assertEqual(command[command.index(flag) + 1], value)
            self.assertNotIn("--dataset_config", command)
            self.assertNotIn("--eval_do_concat_batches", command)
            self.assertFalse((root / "runs" / "new").exists())

            # Without a validation folder, the trainer creates its own held-out split.
            index = arguments.index("--validation-dir")
            del arguments[index : index + 2]
            result = subprocess.run(arguments, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            command = shlex.split(result.stdout)
            self.assertNotIn("--validation_dir", command)
            self.assertEqual(command[command.index("--train_val_split") + 1], "0.15")


if __name__ == "__main__":
    unittest.main()

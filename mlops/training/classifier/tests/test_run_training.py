import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "run_training.py"


class ClassifierCommandTest(unittest.TestCase):
    def test_empty_validation_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("Training", "model"):
                (root / name).mkdir()
            for value in ("", "   "):
                with self.subTest(value=value):
                    result = subprocess.run(
                        [
                            sys.executable, str(SCRIPT),
                            "--dataset-root", str(root),
                            "--train-dir", "Training", "--model-path", "model",
                            "--run-profile", "smoke", "--run-id", "test",
                            "--validation-dir", value, "--dry-run",
                        ],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(
                        "--validation-dir must be a directory or none", result.stderr
                    )

    def test_relative_paths_remain_absolute_in_trainer_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("Training", "Validation", "model"):
                (root / "dataset" / name).mkdir(parents=True)
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT.resolve()),
                    "--dataset-root", "dataset", "--train-dir", "Training",
                    "--validation-dir", "Validation", "--model-path", "model",
                    "--runs-root", "runs", "--run-id", "new",
                    "--run-profile", "smoke", "--dry-run",
                ],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            command = shlex.split(result.stdout)
            for flag, expected in {
                "--train_dir": root / "dataset" / "Training",
                "--validation_dir": root / "dataset" / "Validation",
                "--model_name_or_path": root / "dataset" / "model",
                "--output_dir": root / "runs" / "new" / "trainer-output",
            }.items():
                actual = Path(command[command.index(flag) + 1])
                self.assertTrue(actual.is_absolute())
                self.assertEqual(actual.resolve(), expected.resolve())

    def test_smoke_inputs_overrides_and_resume(self):
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

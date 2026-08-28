import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "run_training.py"


class RunTrainingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.dataset = self.root / "dataset"
        self.dataset.mkdir()
        self.config = self.dataset / "training.yaml"
        self.config.write_text("sources: []\n", encoding="utf-8")
        self.model = self.dataset / "model"
        self.model.mkdir()
        self.runs = self.root / "runs"
        self.trainer = self.root / "train_detector.py"
        self.trainer.write_text("print('not executed')\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def write_complete_checkpoint(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for filename in (
            "model.safetensors",
            "optimizer.pt",
            "rng_state.pth",
            "scheduler.pt",
            "trainer_state.json",
            "training_args.bin",
        ):
            (path / filename).write_text(filename, encoding="utf-8")

    def command(self) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--dataset-root",
            str(self.dataset),
            "--dataset-config",
            self.config.name,
            "--model-path",
            self.model.name,
            "--run-profile",
            "smoke",
            "--run-id",
            "test-run",
            "--runs-root",
            str(self.runs),
            "--trainer-path",
            str(self.trainer),
        ]

    def run_dry(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*self.command(), "--dry-run", *extra],
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def command_value(command: list[str], name: str) -> str:
        return command[command.index(name) + 1]

    def runtime_environment(self, module_directory: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "MLFLOW_EXPERIMENT_NAME": "test-experiment",
                "MLFLOW_PUBLIC_URL": "https://mlflow.test",
                "PYTHONPATH": str(module_directory),
            }
        )
        return environment

    def fake_runtime_modules(self, *, artifact_error: bool = False) -> Path:
        fake_modules = self.root / "fake-modules"
        fake_modules.mkdir(exist_ok=True)
        (fake_modules / "torch.py").write_text(
            """
class cuda:
    @staticmethod
    def is_available():
        return True
""".lstrip(),
            encoding="utf-8",
        )
        artifact_statement = (
            'raise RuntimeError("artifact unavailable")'
            if artifact_error
            else "return None"
        )
        (fake_modules / "mlflow.py").write_text(
            f"""
import os
from pathlib import Path

class _Experiment:
    experiment_id = "fake-experiment-id"

class _Info:
    run_id = "fake-run-id"
    experiment_id = "fake-experiment-id"

class _Run:
    info = _Info()

def set_experiment(_name):
    return _Experiment()

class MlflowClient:
    def create_run(self, _experiment_id, tags=None):
        return _Run()

    def get_run(self, _run_id):
        return _Run()

    def log_artifact(self, _run_id, _path, artifact_path=None):
        {artifact_statement}

    def set_terminated(self, _run_id, status=None):
        status_path = os.environ.get("MLFLOW_STATUS_FILE")
        if status_path:
            with Path(status_path).open("a", encoding="utf-8") as handle:
                handle.write(status + "\\n")
""".lstrip(),
            encoding="utf-8",
        )
        return fake_modules

    def test_smoke_profile_prints_a_bounded_command(self) -> None:
        result = self.run_dry()

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(self.command_value(command, "--num_train_epochs"), "1")
        self.assertIn("--max_train_samples", command)
        self.assertIn("--max_eval_samples", command)
        self.assertFalse((self.runs / "test-run").exists())

    def test_full_profile_keeps_the_launcher_settings(self) -> None:
        result = self.run_dry("--run-profile", "full")

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        expected = {
            "--num_train_epochs": "50",
            "--image_square_size": "640",
            "--per_device_train_batch_size": "24",
            "--gradient_accumulation_steps": "1",
            "--warmup_steps": "760",
            "--learning_rate": "0.00001",
            "--seed": "2438",
        }
        for argument, value in expected.items():
            with self.subTest(argument=argument):
                self.assertEqual(self.command_value(command, argument), value)
        self.assertNotIn("--max_train_samples", command)
        self.assertNotIn("--max_eval_samples", command)

    def test_profile_values_can_be_overridden(self) -> None:
        result = self.run_dry(
            "--batch-size",
            "7",
            "--learning-rate",
            "0.0002",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(
            self.command_value(command, "--per_device_train_batch_size"),
            "7",
        )
        self.assertEqual(self.command_value(command, "--learning_rate"), "0.0002")

    def test_absolute_dataset_inputs_are_accepted(self) -> None:
        external_config = self.root / "fiftyone-output.yaml"
        external_config.write_text("sources: []\n", encoding="utf-8")
        external_model = self.root / "base-model"
        external_model.mkdir()

        result = self.run_dry(
            "--dataset-config",
            str(external_config),
            "--model-path",
            str(external_model),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(
            self.command_value(command, "--dataset_config"),
            str(external_config),
        )
        self.assertEqual(
            self.command_value(command, "--model_name_or_path"),
            str(external_model),
        )

    def test_missing_dataset_config_is_rejected(self) -> None:
        result = self.run_dry("--dataset-config", "missing.yaml")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dataset configuration does not exist", result.stderr)

    def test_resume_uses_the_latest_complete_checkpoint(self) -> None:
        previous_run = self.runs / "previous-run"
        complete = previous_run / "trainer-output" / "checkpoint-40"
        self.write_complete_checkpoint(complete)
        partial = previous_run / "trainer-output" / "checkpoint-50"
        partial.mkdir()
        (partial / "model.safetensors").write_text("weights", encoding="utf-8")
        (previous_run / "mlflow-run-id").write_text(
            "existing-mlflow-run\n",
            encoding="utf-8",
        )

        result = self.run_dry(
            "--resume-run-id",
            "previous-run",
            "--resume-checkpoint",
            "latest",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(
            self.command_value(command, "--resume_from_checkpoint"),
            str(complete),
        )

    def test_missing_cuda_stops_before_training(self) -> None:
        trainer_marker = self.root / "trainer-started"
        self.trainer.write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['TRAINER_MARKER']).touch()\n",
            encoding="utf-8",
        )
        fake_modules = self.fake_runtime_modules()
        (fake_modules / "torch.py").write_text(
            "class cuda:\n"
            "    @staticmethod\n"
            "    def is_available():\n"
            "        return False\n",
            encoding="utf-8",
        )
        environment = self.runtime_environment(fake_modules)
        environment["TRAINER_MARKER"] = str(trainer_marker)

        result = subprocess.run(
            self.command(),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CUDA is not available", result.stderr)
        self.assertFalse(trainer_marker.exists())
        self.assertFalse((self.runs / "test-run").exists())

    def test_artifact_failure_stops_before_training(self) -> None:
        trainer_marker = self.root / "trainer-started"
        self.trainer.write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['TRAINER_MARKER']).touch()\n",
            encoding="utf-8",
        )
        environment = self.runtime_environment(
            self.fake_runtime_modules(artifact_error=True)
        )
        environment["TRAINER_MARKER"] = str(trainer_marker)

        result = subprocess.run(
            self.command(),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifact unavailable", result.stderr)
        self.assertFalse(trainer_marker.exists())

    def test_process_status_and_output_are_retained(self) -> None:
        fake_modules = self.fake_runtime_modules()
        self.trainer.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['TRAINER_RUN_ID_FILE']).write_text(\n"
            "    os.environ['MLFLOW_RUN_ID'], encoding='utf-8'\n"
            ")\n"
            "Path(os.environ['TRAINER_ARTIFACT_LOGGING_FILE']).write_text(\n"
            "    os.environ['HF_MLFLOW_LOG_ARTIFACTS'], encoding='utf-8'\n"
            ")\n"
            "print('trainer-output')\n"
            "raise SystemExit(int(os.environ['TRAINER_EXIT_CODE']))\n",
            encoding="utf-8",
        )

        for exit_code in (0, 9):
            with self.subTest(exit_code=exit_code):
                run_id = f"status-{exit_code}"
                environment = self.runtime_environment(fake_modules)
                environment["TRAINER_EXIT_CODE"] = str(exit_code)
                status_file = self.root / f"{run_id}-status"
                trainer_run_id_file = self.root / f"{run_id}-mlflow-run-id"
                artifact_logging_file = self.root / f"{run_id}-artifact-logging"
                environment["MLFLOW_STATUS_FILE"] = str(status_file)
                environment["TRAINER_RUN_ID_FILE"] = str(trainer_run_id_file)
                environment["TRAINER_ARTIFACT_LOGGING_FILE"] = str(
                    artifact_logging_file
                )

                command = self.command()
                command[command.index("test-run")] = run_id
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )

                self.assertEqual(result.returncode, exit_code, result.stderr)
                run_root = self.runs / run_id
                self.assertEqual(trainer_run_id_file.read_text(), "fake-run-id")
                self.assertEqual(artifact_logging_file.read_text(), "TRUE")
                self.assertEqual(
                    (run_root / "mlflow-run-id").read_text(),
                    "fake-run-id\n",
                )
                self.assertEqual(
                    (run_root / "mlflow-run-url").read_text(),
                    (
                        "https://mlflow.test/#/experiments/"
                        "fake-experiment-id/runs/fake-run-id\n"
                    ),
                )
                self.assertEqual(
                    status_file.read_text().splitlines(),
                    ["FINISHED" if exit_code == 0 else "FAILED"],
                )
                self.assertEqual(
                    (run_root / "exit-code").read_text(),
                    f"{exit_code}\n",
                )
                self.assertEqual(
                    (run_root / "train_log.txt").read_text().strip(),
                    "trainer-output",
                )

    def test_sigterm_is_forwarded_to_the_trainer(self) -> None:
        fake_modules = self.fake_runtime_modules()
        started = self.root / "trainer-started"
        stopped = self.root / "trainer-stopped"
        self.trainer.write_text(
            "import os\n"
            "import signal\n"
            "import time\n"
            "from pathlib import Path\n"
            "def stop(_signum, _frame):\n"
            "    Path(os.environ['TRAINER_STOPPED']).touch()\n"
            "    raise SystemExit(23)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "Path(os.environ['TRAINER_STARTED']).touch()\n"
            "while True:\n"
            "    time.sleep(0.05)\n",
            encoding="utf-8",
        )
        environment = self.runtime_environment(fake_modules)
        status_file = self.root / "signal-status"
        environment["MLFLOW_STATUS_FILE"] = str(status_file)
        environment["TRAINER_STARTED"] = str(started)
        environment["TRAINER_STOPPED"] = str(stopped)
        process = subprocess.Popen(
            self.command(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        deadline = time.monotonic() + 5
        while not started.exists() and process.poll() is None:
            if time.monotonic() >= deadline:
                process.kill()
                self.fail("trainer did not start before the timeout")
            time.sleep(0.05)

        process.send_signal(signal.SIGTERM)
        _stdout, stderr = process.communicate(timeout=5)

        self.assertEqual(process.returncode, 23, stderr)
        self.assertTrue(stopped.exists())
        self.assertEqual(status_file.read_text().splitlines(), ["FAILED"])


if __name__ == "__main__":
    unittest.main()

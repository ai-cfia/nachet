import os
import shlex
import subprocess
import sys
import tempfile
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

    def run_runtime(
        self,
        environment: dict[str, str],
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*self.command(), *extra],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
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

    def fake_runtime_modules(self) -> Path:
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
        return None

    def set_terminated(self, _run_id, status=None):
        status_path = os.environ.get("MLFLOW_STATUS_FILE")
        if status_path:
            with Path(status_path).open("a", encoding="utf-8") as handle:
                handle.write(status + "\\n")
""".lstrip(),
            encoding="utf-8",
        )
        return fake_modules

    def write_recording_trainer(self) -> tuple[Path, Path]:
        arguments_file = self.root / "trainer-arguments"
        run_id_file = self.root / "trainer-run-id"
        self.trainer.write_text(
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['TRAINER_ARGUMENTS_FILE']).write_text(\n"
            "    '\\n'.join(sys.argv[1:]), encoding='utf-8'\n"
            ")\n"
            "Path(os.environ['TRAINER_RUN_ID_FILE']).write_text(\n"
            "    os.environ['MLFLOW_RUN_ID'], encoding='utf-8'\n"
            ")\n"
            "print('trainer attempt')\n",
            encoding="utf-8",
        )
        return arguments_file, run_id_file

    def test_smoke_profile_prints_a_bounded_command(self) -> None:
        result = self.run_dry()

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(self.command_value(command, "--num_train_epochs"), "1")
        self.assertEqual(self.command_value(command, "--save_total_limit"), "1")
        self.assertIn("--max_train_samples", command)
        self.assertIn("--max_eval_samples", command)
        self.assertFalse((self.runs / "test-run").exists())

    def test_profile_values_can_be_overridden(self) -> None:
        result = self.run_dry(
            "--batch-size",
            "7",
            "--learning-rate",
            "0.0002",
            "--checkpoint-retention",
            "4",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(
            self.command_value(command, "--per_device_train_batch_size"),
            "7",
        )
        self.assertEqual(self.command_value(command, "--learning_rate"), "0.0002")
        self.assertEqual(self.command_value(command, "--save_total_limit"), "4")

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

    def test_completed_run_returns_success_without_running_again(self) -> None:
        run_root = self.runs / "test-run"
        run_root.mkdir(parents=True)
        (run_root / "exit-code").write_text("0\n", encoding="utf-8")
        trainer_marker = self.root / "trainer-started"
        self.trainer.write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['TRAINER_MARKER']).touch()\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["TRAINER_MARKER"] = str(trainer_marker)

        result = self.run_runtime(environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(trainer_marker.exists())
        self.assertEqual((run_root / "exit-code").read_text(), "0\n")

    def test_required_mlflow_configuration_is_validated(self) -> None:
        fake_modules = self.fake_runtime_modules()
        run_id_path = self.runs / "test-run" / "mlflow-run-id"

        for variable in ("MLFLOW_PUBLIC_URL", "MLFLOW_EXPERIMENT_NAME"):
            with self.subTest(variable=variable):
                environment = self.runtime_environment(fake_modules)
                environment.pop(variable)

                result = self.run_runtime(environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(variable, result.stderr)
                self.assertFalse(run_id_path.exists())

    def test_retry_resumes_latest_checkpoint_and_reuses_mlflow_run(self) -> None:
        run_root = self.runs / "test-run"
        complete = run_root / "trainer-output" / "checkpoint-40"
        self.write_complete_checkpoint(complete)
        partial = run_root / "trainer-output" / "checkpoint-50"
        partial.mkdir()
        (partial / "model.safetensors").write_text("weights", encoding="utf-8")
        (run_root / "mlflow-run-id").write_text(
            "existing-mlflow-run\n",
            encoding="utf-8",
        )
        (run_root / "exit-code").write_text("9\n", encoding="utf-8")
        (run_root / "train_log.txt").write_text(
            "first attempt\n",
            encoding="utf-8",
        )
        arguments_file, trainer_run_id_file = self.write_recording_trainer()
        environment = self.runtime_environment(self.fake_runtime_modules())
        environment.pop("MLFLOW_EXPERIMENT_NAME")
        environment["TRAINER_ARGUMENTS_FILE"] = str(arguments_file)
        environment["TRAINER_RUN_ID_FILE"] = str(trainer_run_id_file)

        result = self.run_runtime(environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = arguments_file.read_text().splitlines()
        self.assertEqual(
            self.command_value(arguments, "--resume_from_checkpoint"),
            str(complete),
        )
        self.assertEqual(trainer_run_id_file.read_text(), "existing-mlflow-run")
        self.assertFalse(partial.exists())
        self.assertEqual((run_root / "exit-code").read_text(), "0\n")
        self.assertEqual(
            (run_root / "train_log.txt").read_text(),
            "first attempt\n\n--- retry ---\ntrainer attempt\n",
        )

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

if __name__ == "__main__":
    unittest.main()

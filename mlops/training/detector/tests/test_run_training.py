from argparse import Namespace
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).parents[1] / "src" / "run_training.py"
sys.path.insert(0, str(SCRIPT.parents[2]))
from training_runtime import execute_training  # noqa: E402


class RunTrainingTest(unittest.TestCase):
    def test_relative_paths_remain_absolute_in_trainer_command(self):
        result = subprocess.run(
            [
                *self.command(), "--dry-run",
                "--dataset-root", "dataset", "--runs-root", "runs",
                "--trainer-path", "train_detector.py",
            ],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        for flag, expected in {
            "--dataset_config": self.config,
            "--model_name_or_path": self.model,
            "--output_dir": self.runs / "test-run" / "trainer-output",
        }.items():
            actual = Path(command[command.index(flag) + 1])
            self.assertTrue(actual.is_absolute())
            self.assertEqual(actual.resolve(), expected.resolve())
        self.assertTrue(Path(command[1]).is_absolute())
        self.assertEqual(Path(command[1]).resolve(), self.trainer.resolve())

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
        # The launcher imports Transformers, so torch must be real; CI has no GPU.
        (fake_modules / "sitecustomize.py").write_text(
            "import torch\ntorch.cuda.is_available = lambda: True\n",
            encoding="utf-8",
        )
        (fake_modules / "mlflow.py").write_text(
            """
import os
import json
from pathlib import Path
from types import SimpleNamespace

class _Experiment:
    experiment_id = "fake-experiment-id"

class _Info:
    run_id = "fake-run-id"
    experiment_id = "fake-experiment-id"

class _Run:
    info = _Info()
    data = SimpleNamespace(params=json.loads(os.environ.get("MLFLOW_PARAMS", "{}")))

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

        full = self.run_dry("--run-profile", "full")
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertEqual(
            self.command_value(shlex.split(full.stdout), "--save_total_limit"), "2"
        )

    def test_profile_values_can_be_overridden(self) -> None:
        result = self.run_dry(
            "--image-size",
            "512",
            "--batch-size",
            "7",
            "--learning-rate",
            "0.0002",
            "--checkpoint-retention",
            "4",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        command = shlex.split(result.stdout)
        self.assertEqual(self.command_value(command, "--image_square_size"), "512")
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

    def test_small_learning_rate_is_preserved(self):
        result = self.run_dry("--learning-rate", "1e-16")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            float(self.command_value(shlex.split(result.stdout), "--learning_rate")),
            1e-16,
        )

    def test_pvc_training_cannot_resume_a_release_checkpoint(self) -> None:
        previous_run = self.runs / "previous-run"
        self.write_complete_checkpoint(previous_run / "trainer-output" / "checkpoint-40")
        (previous_run / "mlflow-run-id").write_text("release-run\n", encoding="utf-8")
        environment = self.runtime_environment(self.fake_runtime_modules())
        environment["MLFLOW_PARAMS"] = '{"dataset_release_id": "reviewed-release"}'

        result = self.run_runtime(environment, "--resume-run-id", "previous-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Training data release differs", result.stderr)
        self.assertFalse((self.runs / "test-run").exists())

    def test_archive_restore_waits_for_release_identity_validation(self) -> None:
        reference = {"dataset_release_id": "reviewed", "dataset_manifest_sha256": "a" * 64}
        for retry in (False, True):
            for outcome in ("mismatch", "matching", "dry-run"):
                with self.subTest(retry=retry, outcome=outcome):
                    run_id = f"restore-{retry}-{outcome}"
                    source = self.runs / (run_id if retry else f"source-{run_id}")
                    output = source / "trainer-output"
                    output.mkdir(parents=True)
                    (source / "mlflow-run-id").write_text("previous-mlflow-run\n")
                    checkpoint = output / "checkpoint-40"
                    args = Namespace(
                        runs_root=self.runs, run_id=run_id, dataset_root=self.dataset,
                        resume_run_id=None if retry else source.name,
                        resume_runs_root=None, resume_checkpoint="checkpoint-40",
                        dry_run=outcome == "dry-run",
                    )
                    params = dict(reference)
                    if outcome == "mismatch":
                        params["dataset_manifest_sha256"] = "b" * 64
                    client = Mock()
                    client.get_run.return_value = SimpleNamespace(
                        data=SimpleNamespace(params=params),
                        info=SimpleNamespace(experiment_id="experiment"),
                    )

                    def download(*, artifact_uri, dst_path):
                        model = Path(dst_path) / "model"
                        self.write_complete_checkpoint(model / "artifacts" / checkpoint.name)
                        return str(model)

                    downloads = Mock(side_effect=download)
                    trainer = Mock(return_value=0)
                    archives = {checkpoint.name: "archived-model"}
                    with (
                        patch.dict(os.environ, {"MLFLOW_PUBLIC_URL": "https://mlflow.test"}),
                        patch("mlflow.artifacts.download_artifacts", downloads),
                        patch("training_runtime.archived_checkpoints", return_value=archives),
                        patch("checkpoints.archived_checkpoints", return_value=archives),
                        patch("training_runtime.validate_runtime"),
                        patch("training_runtime.get_or_create_mlflow_run", return_value=(client, "previous-mlflow-run")),
                        patch("training_runtime.run_and_tee", trainer),
                    ):
                        def command(_output, resume):
                            return ["train", str(resume)]
                        if outcome == "mismatch":
                            with self.assertRaisesRegex(ValueError, "Training data release differs"):
                                execute_training(args, command, release_reference=reference)
                        else:
                            self.assertEqual(execute_training(args, command, release_reference=reference), 0)
                    if outcome == "matching":
                        downloads.assert_called_once()
                        self.assertTrue(checkpoint.is_dir())
                        trainer.assert_called_once()
                        self.assertEqual(trainer.call_args.args[0], ["train", str(checkpoint)])
                    else:
                        downloads.assert_not_called()
                        trainer.assert_not_called()
                        client.set_terminated.assert_not_called()
                        self.assertEqual(list(output.iterdir()), [])
                        self.assertEqual((source / "mlflow-run-id").read_text(), "previous-mlflow-run\n")
                        if not retry:
                            self.assertFalse((self.runs / run_id).exists())

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

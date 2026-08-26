import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "src" / "run_training.py"
SOURCE_DIRECTORY = SCRIPT.parent
REVIEWED_SOURCE_HASHES = {
    "train_detector.py": (
        "458a96369d8c99775c387b097ef2addd7ca225519a4aaaec3420840d4d3bf94b"
    ),
    "coco_to_hf_dataset.py": (
        "94b99c977de3a228b6fcf4851804c61a183a77d81a49017bfcf96dfc9d04f9b4"
    ),
}


class RunTrainingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.inputs = self.root / "inputs"
        self.runs = self.root / "runs"
        self.write_dataset_profile(
            "detector-smoke-v1",
            "training_config_smoke.yaml",
        )
        self.write_dataset_profile(
            "101-species-v1",
            "training_config_101spp_all.yaml",
        )
        self.trainer = self.root / "train_detector.py"
        self.trainer.write_text("print('not executed')\n", encoding="utf-8")

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

    def write_dataset_profile(self, name: str, config_name: str) -> None:
        # Separate roots prevent the smoke profile from resolving full-dataset files.
        profile = (self.inputs / name).resolve()
        config = profile / "notebooks" / "shell" / config_name
        config.parent.mkdir(parents=True)
        included_classes = (
            [f"Species {index}" for index in range(1, 102)]
            if name == "101-species-v1"
            else ["Agrostemma githago"]
        )
        data = profile / "data"
        (data / "images").mkdir(parents=True)
        (data / "annotations.json").write_text(
            json.dumps(
                {
                    "categories": [
                        {"id": index, "name": class_name}
                        for index, class_name in enumerate(included_classes, start=1)
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (data / "reject.txt").write_text("", encoding="utf-8")
        config.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "json_path": "data/annotations.json",
                            "images_dir": "data/images",
                            "reject_list": "data/reject.txt",
                        }
                    ],
                    "include_classes": included_classes,
                    "single_category": True,
                    "single_category_name": "seed",
                }
            ),
            encoding="utf-8",
        )
        (profile / "models" / "rtdetr_v2_r50vd").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def command(self) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--dataset-profile",
            "detector-smoke-v1",
            "--run-profile",
            "smoke",
            "--gpu-profile",
            "ai-lab-1",
            "--run-id",
            "test-run",
            "--input-root",
            str(self.inputs),
            "--runs-root",
            str(self.runs),
            "--trainer-path",
            str(self.trainer),
        ]

    def run_script(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*self.command(), "--dry-run", *extra],
            check=False,
            capture_output=True,
            text=True,
        )

    def runtime_environment(self, module_directory: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "AWS_ACCESS_KEY_ID": "test-access-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret-key",
                "KUBERNETES_NODE_NAME": "ai-lab-1",
                "MLFLOW_ARTIFACT_BUCKET": "test-bucket",
                "MLFLOW_EXPERIMENT_NAME": "test-experiment",
                "MLFLOW_PUBLIC_URL": "https://mlflow.test",
                "MLFLOW_S3_ENDPOINT_URL": "http://s3.test",
                "MLFLOW_TRACKING_URI": "http://mlflow.test",
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

    @staticmethod
    def device_count():
        return 1
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

    def test_migrated_training_sources_match_recorded_provenance(self) -> None:
        for filename, expected_hash in REVIEWED_SOURCE_HASHES.items():
            with self.subTest(filename=filename):
                contents = (SOURCE_DIRECTORY / filename).read_bytes()
                self.assertEqual(hashlib.sha256(contents).hexdigest(), expected_hash)

    def test_smoke_profile_writes_a_bounded_command_and_receipt(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.runs / "test-run" / "request.json").read_text())
        self.assertEqual(receipt["gpu_profile"], "ai-lab-1")
        self.assertEqual(receipt["dataset_source_count"], 1)
        annotation_path = (
            self.inputs / "detector-smoke-v1" / "data" / "annotations.json"
        )
        self.assertEqual(
            receipt["dataset_sources"],
            [
                {
                    "json_path": "data/annotations.json",
                    "json_sha256": hashlib.sha256(
                        annotation_path.read_bytes()
                    ).hexdigest(),
                    "images_dir": "data/images",
                    "reject_list": "data/reject.txt",
                    "reject_list_sha256": hashlib.sha256(b"").hexdigest(),
                    "matched_classes": ["Agrostemma githago"],
                }
            ],
        )
        self.assertEqual(receipt["included_class_count"], 1)
        self.assertEqual(
            receipt["included_classes_sha256"],
            hashlib.sha256(b'["Agrostemma githago"]').hexdigest(),
        )
        self.assertIn("--max_train_samples", receipt["command"])
        self.assertIn("--max_eval_samples", receipt["command"])
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", json.dumps(receipt))

    def test_unknown_gpu_profile_is_rejected_by_the_parser(self) -> None:
        result = self.run_script("--gpu-profile", "arbitrary-node")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_reviewed_profile_values_can_be_overridden_explicitly(self) -> None:
        result = self.run_script(
            "--batch-size",
            "7",
            "--learning-rate",
            "0.0002",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.runs / "test-run" / "request.json").read_text())
        parameters = receipt["effective_training_parameters"]
        self.assertEqual(parameters["batch_size"], 7)
        self.assertEqual(parameters["learning_rate"], 0.0002)
        command = receipt["command"]
        self.assertEqual(command[command.index("--learning_rate") + 1], "0.0002")

    def test_full_profile_keeps_the_reviewed_launcher_settings(self) -> None:
        result = self.run_script(
            "--dataset-profile",
            "101-species-v1",
            "--run-profile",
            "full",
            "--run-id",
            "full-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.runs / "full-run" / "request.json").read_text())
        command = receipt["command"]
        profile = (self.inputs / "101-species-v1").resolve()
        expected_arguments = [
            "--do_train",
            "--do_eval",
            "--dataset_config",
            str(profile / "notebooks/shell/training_config_101spp_all.yaml"),
            "--train_val_split",
            "0.15",
            "--output_dir",
            str((self.runs / "full-run" / "trainer-output").resolve()),
            "--num_train_epochs",
            "50",
            "--image_square_size",
            "640",
            "--per_device_train_batch_size",
            "24",
            "--dataloader_num_workers",
            "0",
            "--gradient_accumulation_steps",
            "1",
            "--warmup_steps",
            "760",
            "--learning_rate",
            "0.00001",
            "--seed",
            "2438",
            "--eval_strategy",
            "epoch",
            "--save_strategy",
            "epoch",
            "--logging_strategy",
            "steps",
            "--logging_steps",
            "50",
            "--report_to",
            "mlflow",
            "--save_total_limit",
            "50",
            "--bf16",
            "--ignore_mismatched_sizes",
            "--remove_unused_columns",
            "false",
            "--eval_do_concat_batches",
            "false",
            "--model_name_or_path",
            str(profile / "models/rtdetr_v2_r50vd"),
        ]
        self.assertEqual(command[2:], expected_arguments)

    def test_full_run_rejects_the_temporary_smoke_dataset(self) -> None:
        result = self.run_script("--run-profile", "full", "--run-id", "full-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "run profile 'full' is not allowed with dataset profile "
            "'detector-smoke-v1'",
            result.stderr,
        )
        self.assertFalse((self.runs / "full-run").exists())

    def test_101_species_profile_requires_101_selected_classes(self) -> None:
        config = (
            self.inputs
            / "101-species-v1"
            / "notebooks"
            / "shell"
            / "training_config_101spp_all.yaml"
        )
        value = json.loads(config.read_text(encoding="utf-8"))
        value["include_classes"] = value["include_classes"][:-1]
        config.write_text(json.dumps(value), encoding="utf-8")

        result = self.run_script(
            "--dataset-profile",
            "101-species-v1",
            "--run-id",
            "class-count-run",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires 101 included classes, found 100", result.stderr)
        self.assertFalse((self.runs / "class-count-run").exists())

    def test_selected_class_must_exist_in_a_coco_category_table(self) -> None:
        config = (
            self.inputs
            / "detector-smoke-v1"
            / "notebooks"
            / "shell"
            / "training_config_smoke.yaml"
        )
        value = json.loads(config.read_text(encoding="utf-8"))
        value["include_classes"] = ["Missing species"]
        config.write_text(json.dumps(value), encoding="utf-8")

        result = self.run_script()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "absent from the COCO category tables: Missing species",
            result.stderr,
        )
        self.assertFalse((self.runs / "test-run").exists())

    def test_resume_uses_a_checkpoint_and_the_existing_mlflow_run(self) -> None:
        previous_run = self.runs / "previous-run"
        checkpoint = previous_run / "trainer-output" / "checkpoint-40"
        self.write_complete_checkpoint(checkpoint)
        (previous_run / "mlflow-run-id").write_text(
            "existing-mlflow-run\n",
            encoding="utf-8",
        )

        result = self.run_script(
            "--resume-run-id",
            "previous-run",
            "--resume-checkpoint",
            "latest",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.runs / "test-run" / "request.json").read_text())
        self.assertEqual(receipt["resume_run_id"], "previous-run")
        self.assertEqual(receipt["resume_checkpoint"], str(checkpoint.resolve()))
        self.assertEqual(
            receipt["command"][-2:],
            ["--resume_from_checkpoint", str(checkpoint.resolve())],
        )

    def test_preflight_reads_resume_state_from_the_persistent_root(self) -> None:
        previous_run = self.runs / "previous-run"
        checkpoint = previous_run / "trainer-output" / "checkpoint-40"
        self.write_complete_checkpoint(checkpoint)
        (previous_run / "mlflow-run-id").write_text(
            "existing-mlflow-run\n",
            encoding="utf-8",
        )
        validation_runs = self.root / "validation-runs"

        result = self.run_script(
            "--runs-root",
            str(validation_runs),
            "--resume-runs-root",
            str(self.runs),
            "--resume-run-id",
            "previous-run",
            "--resume-checkpoint",
            "checkpoint-40",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(
            (validation_runs / "test-run" / "request.json").read_text()
        )
        self.assertEqual(receipt["resume_checkpoint"], str(checkpoint.resolve()))

    def test_resume_skips_a_newer_partial_checkpoint(self) -> None:
        previous_run = self.runs / "previous-run"
        completed = previous_run / "trainer-output" / "checkpoint-40"
        self.write_complete_checkpoint(completed)
        partial = previous_run / "trainer-output" / "checkpoint-50"
        partial.mkdir()
        (partial / "model.safetensors").write_text("weights", encoding="utf-8")
        (previous_run / "mlflow-run-id").write_text(
            "existing-mlflow-run\n",
            encoding="utf-8",
        )

        result = self.run_script(
            "--resume-run-id",
            "previous-run",
            "--resume-checkpoint",
            "latest",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.runs / "test-run" / "request.json").read_text())
        self.assertEqual(receipt["resume_checkpoint"], str(completed.resolve()))

    def test_invalid_run_id_is_rejected_before_output_is_created(self) -> None:
        result = self.run_script("--run-id", "../escape")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "escape").exists())

    def test_dataset_source_cannot_leave_the_reviewed_snapshot(self) -> None:
        config = (
            self.inputs
            / "detector-smoke-v1"
            / "notebooks"
            / "shell"
            / "training_config_smoke.yaml"
        )
        config.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "json_path": "/etc/passwd",
                            "images_dir": "data/images",
                        }
                    ],
                    "include_classes": ["Agrostemma githago"],
                    "single_category": True,
                    "single_category_name": "seed",
                }
            ),
            encoding="utf-8",
        )

        result = self.run_script()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("path leaves its approved root", result.stderr)

    def test_dataset_profile_requires_a_class_selection(self) -> None:
        config = (
            self.inputs
            / "detector-smoke-v1"
            / "notebooks"
            / "shell"
            / "training_config_smoke.yaml"
        )
        value = json.loads(config.read_text(encoding="utf-8"))
        value.pop("include_classes")
        config.write_text(json.dumps(value), encoding="utf-8")

        result = self.run_script()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-empty include_classes list", result.stderr)

    def test_dataset_profile_rejects_duplicate_class_names(self) -> None:
        config = (
            self.inputs
            / "detector-smoke-v1"
            / "notebooks"
            / "shell"
            / "training_config_smoke.yaml"
        )
        value = json.loads(config.read_text(encoding="utf-8"))
        value["include_classes"] = ["Agrostemma githago", "agrostemma githago"]
        config.write_text(json.dumps(value), encoding="utf-8")

        result = self.run_script()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unique ignoring case", result.stderr)

    def test_dataset_profile_requires_single_seed_category(self) -> None:
        config = (
            self.inputs
            / "detector-smoke-v1"
            / "notebooks"
            / "shell"
            / "training_config_smoke.yaml"
        )
        value = json.loads(config.read_text(encoding="utf-8"))
        value["single_category"] = False
        config.write_text(json.dumps(value), encoding="utf-8")

        result = self.run_script()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must set single_category: true", result.stderr)

    def test_resume_rejects_a_symlinked_checkpoint(self) -> None:
        previous_run = self.runs / "previous-run"
        actual_checkpoint = previous_run / "trainer-output" / "checkpoint-20"
        actual_checkpoint.mkdir(parents=True)
        (previous_run / "trainer-output" / "checkpoint-40").symlink_to(
            actual_checkpoint,
            target_is_directory=True,
        )
        (previous_run / "mlflow-run-id").write_text(
            "existing-mlflow-run\n",
            encoding="utf-8",
        )

        result = self.run_script(
            "--resume-run-id",
            "previous-run",
            "--resume-checkpoint",
            "checkpoint-40",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertFalse((self.runs / "test-run").exists())

    def test_node_mismatch_stops_before_the_trainer_is_started(self) -> None:
        trainer_marker = self.root / "trainer-started"
        self.trainer.write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['TRAINER_MARKER']).touch()\n",
            encoding="utf-8",
        )
        environment = self.runtime_environment(self.fake_runtime_modules())
        environment["KUBERNETES_NODE_NAME"] = "ai-lab-2"
        environment["TRAINER_MARKER"] = str(trainer_marker)

        result = subprocess.run(
            self.command(),
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requested GPU profile ai-lab-1", result.stderr)
        self.assertFalse(trainer_marker.exists())
        failure = json.loads((self.runs / "test-run" / "result.json").read_text())
        self.assertEqual(failure["status"], "failed")
        self.assertEqual(failure["error_type"], "RuntimeError")

    def test_artifact_failure_stops_before_the_trainer_is_started(self) -> None:
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

    def test_process_result_and_output_are_retained(self) -> None:
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
                result_record = json.loads(
                    (self.runs / run_id / "result.json").read_text()
                )
                self.assertEqual(
                    result_record,
                    {
                        "status": "succeeded" if exit_code == 0 else "failed",
                        "exit_code": exit_code,
                        "mlflow_run_id": "fake-run-id",
                        "mlflow_run_url": (
                            "https://mlflow.test/#/experiments/"
                            "fake-experiment-id/runs/fake-run-id"
                        ),
                    },
                )
                self.assertEqual(trainer_run_id_file.read_text(), "fake-run-id")
                self.assertEqual(artifact_logging_file.read_text(), "TRUE")
                self.assertEqual(
                    (self.runs / run_id / "mlflow-experiment-id").read_text(),
                    "fake-experiment-id\n",
                )
                self.assertEqual(
                    (self.runs / run_id / "mlflow-run-url").read_text(),
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
                    (self.runs / run_id / "exit-code").read_text(),
                    f"{exit_code}\n",
                )
                train_log = self.runs / run_id / "train_log.txt"
                self.assertEqual(train_log.read_text().strip(), "trainer-output")

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
        result_record = json.loads((self.runs / "test-run" / "result.json").read_text())
        self.assertEqual(
            result_record,
            {
                "status": "failed",
                "exit_code": 23,
                "mlflow_run_id": "fake-run-id",
                "mlflow_run_url": (
                    "https://mlflow.test/#/experiments/"
                    "fake-experiment-id/runs/fake-run-id"
                ),
            },
        )
        self.assertEqual(status_file.read_text().splitlines(), ["FAILED"])


if __name__ == "__main__":
    unittest.main()

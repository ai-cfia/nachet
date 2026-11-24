"""Exercise native Trainer saves, MLflow artifacts and recovery after rotation."""

from argparse import Namespace
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

import mlflow
from mlflow.store.artifact.local_artifact_repo import LocalArtifactRepository
from safetensors.torch import load_file
import torch
from transformers import Trainer, TrainerCallback, TrainingArguments

TRAINING = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING))
from checkpoints import (  # noqa: E402
    REQUIRED_CHECKPOINT_FILES, RecoverCheckpointArchives, archived_checkpoints,
    resolve_checkpoint, restore,
)
from training_runtime import resolve_resume_checkpoint  # noqa: E402


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(2, 1)

    def forward(self, input_ids, labels):
        logits = self.linear(input_ids)
        return {"loss": torch.nn.functional.mse_loss(logits, labels), "logits": logits}


class CheckpointArchiveTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        previous_uri = mlflow.get_tracking_uri()
        self.environment = patch.dict(os.environ, {
            "MLFLOW_TRACKING_URI": (self.root / "mlruns").as_uri(),
            "HF_MLFLOW_LOG_ARTIFACTS": "TRUE",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(mlflow.set_tracking_uri, previous_uri)
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment("checkpoint-storage")
        torch.set_num_threads(1)
        self.run = self.root / "runs" / "training"
        self.output = self.run / "trainer-output"

    def arguments(self, output):
        return TrainingArguments(
            output_dir=str(output), use_cpu=True, max_steps=4,
            save_strategy="steps", save_steps=1, save_total_limit=2,
            logging_strategy="no", report_to="mlflow", disable_tqdm=True,
            per_device_train_batch_size=1, learning_rate=0.01, seed=2438,
        )

    def fail_third_upload(self):
        native_upload = LocalArtifactRepository.log_artifacts
        uploads = 0

        def upload(repository, local_dir, artifact_path=None):
            nonlocal uploads
            if (Path(local_dir) / "MLmodel").is_file():
                uploads += 1
                if uploads == 3:
                    raise OSError("artifact store unavailable")
            return native_upload(repository, local_dir, artifact_path)

        return patch.object(LocalArtifactRepository, "log_artifacts", upload)

    def test_native_archives_preserve_pruned_checkpoint_and_full_resume_state(self):
        snapshots = {}

        class CaptureSaves(TrainerCallback):
            def on_save(self, args, state, control, **kwargs):
                directory = Path(args.output_dir) / f"checkpoint-{state.global_step}"
                snapshots[directory.name] = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in directory.iterdir() if path.is_file()
                }

        dataset = [{"input_ids": torch.tensor([1.0, 2.0]), "labels": torch.tensor([0.5])}]
        torch.manual_seed(2438)
        with self.assertRaisesRegex(OSError, "artifact store unavailable"):
            with mlflow.start_run() as parent, mlflow.start_run(nested=True):
                self.run.mkdir(parents=True)
                (self.run / "mlflow-run-id").write_text(parent.info.run_id)
                trainer = Trainer(
                    model=TinyModel(), args=self.arguments(self.output),
                    train_dataset=dataset, callbacks=[CaptureSaves()],
                )
                with self.fail_third_upload():
                    trainer.train()

        self.assertEqual(
            sorted(path.name for path in self.output.glob("checkpoint-*")),
            ["checkpoint-2", "checkpoint-3"],
        )
        # Failed model uploads are not candidates. The newest local save survives.
        self.assertEqual(set(archived_checkpoints(self.run)), {"checkpoint-1", "checkpoint-2"})
        options = self.root / "options.json"
        command = [
            sys.executable, str(TRAINING / "checkpoints.py"),
            "--runs-root", str(self.run.parent), "--run-id", self.run.name,
        ]
        result = subprocess.run(
            [*command, "list", "--output", str(options)], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(options.read_text())["enum"], [
            "checkpoint-1", "checkpoint-2", "checkpoint-3",
        ])

        selected = self.root / "selected.json"
        result = subprocess.run([
            *command, "validate-selection", "--checkpoint-options", options.read_text(),
            "--selected-checkpoint", "checkpoint-1", "--output", str(selected),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(selected.read_text()), ["checkpoint-1"])
        restored = self.output / "checkpoint-1"
        self.assertEqual({
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in restored.iterdir() if path.is_file()
        }, snapshots["checkpoint-1"])
        checkpoint, run_id = resolve_resume_checkpoint(self.run.parent, self.run.name, "checkpoint-1")
        self.assertEqual(checkpoint, restored)
        self.assertEqual(run_id, parent.info.run_id)

        expected_weights = load_file(restored / "model.safetensors")
        expected_optimizer = torch.load(restored / "optimizer.pt", weights_only=True)
        expected_scheduler = torch.load(restored / "scheduler.pt", weights_only=True)
        test = self

        class VerifyResume(TrainerCallback):
            def on_train_begin(self, args, state, control, **kwargs):
                test.assertEqual(state.global_step, 1)
                torch.testing.assert_close(kwargs["model"].state_dict(), expected_weights, rtol=0, atol=0)
                torch.testing.assert_close(kwargs["optimizer"].state_dict(), expected_optimizer, rtol=0, atol=0)
                test.assertEqual(kwargs["lr_scheduler"].state_dict(), expected_scheduler)

        # A new training attempt and output directory must recover the full state.
        continuation = self.root / "runs" / "continuation" / "trainer-output"
        with mlflow.start_run(run_id=parent.info.run_id), mlflow.start_run(nested=True):
            resumed = Trainer(
                model=TinyModel(), args=self.arguments(continuation),
                train_dataset=dataset, callbacks=[VerifyResume()],
            )
            resumed.train(resume_from_checkpoint=str(checkpoint))
        self.assertEqual(resumed.state.global_step, 4)
        # The shared parent run must not mix this workflow with its continuation.
        self.assertEqual(set(archived_checkpoints(self.run)), {"checkpoint-1", "checkpoint-2"})
        for path in self.output.glob("checkpoint-*"):
            shutil.rmtree(path)
        latest, _ = resolve_resume_checkpoint(self.run.parent, self.run.name, "latest")
        self.assertEqual(latest.name, "checkpoint-2")
        self.assertEqual({
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in latest.iterdir() if path.is_file()
        }, snapshots["checkpoint-2"])

    def test_dry_run_and_failed_download_leave_no_checkpoint(self):
        self.output.mkdir(parents=True)
        archives = {"checkpoint-1": "m-test"}

        def interrupted_download(*, artifact_uri, dst_path):
            (Path(dst_path) / "partial-model").write_bytes(b"partial")
            raise OSError("download interrupted")

        with patch("mlflow.artifacts.download_artifacts", side_effect=interrupted_download) as download:
            planned = resolve_checkpoint(self.output, "checkpoint-1", archives=archives, download=False)
            self.assertEqual(planned, self.output / "checkpoint-1")
            download.assert_not_called()
            with self.assertRaisesRegex(OSError, "download interrupted"):
                resolve_checkpoint(self.output, "checkpoint-1", archives=archives)
        self.assertEqual(list(self.output.glob("checkpoint-*")), [])
        self.assertEqual(list(self.output.glob(".restore-*")), [])

    def test_restore_replaces_only_an_archived_incomplete_checkpoint(self):
        partial = self.output / "checkpoint-1"
        partial.mkdir(parents=True)
        for name in ("trainer_state.json", "model.safetensors"):
            (partial / name).write_text("partial")
        arguments = Namespace(runs_root=self.run.parent, run_id=self.run.name)

        def download(*, artifact_uri, dst_path):
            restored = Path(dst_path) / "artifacts" / "checkpoint-1"
            restored.mkdir(parents=True)
            for name in (*REQUIRED_CHECKPOINT_FILES, "model.safetensors"):
                (restored / name).write_text("archived")
            return dst_path

        with patch("mlflow.artifacts.download_artifacts", side_effect=download):
            with patch("checkpoints.archived_checkpoints", return_value={}):
                for name in ("checkpoint-1", ".."):
                    with self.assertRaisesRegex(ValueError, "incomplete|invalid"):
                        restore(Namespace(**vars(arguments), checkpoint=name))
                self.assertEqual((partial / "trainer_state.json").read_text(), "partial")
        with patch("checkpoints.archived_checkpoints", return_value={"checkpoint-1": "m-test"}):
            with patch("mlflow.artifacts.download_artifacts", return_value=str(self.run)):
                with self.assertRaisesRegex(ValueError, "archive is incomplete"):
                    restore(Namespace(**vars(arguments), checkpoint="checkpoint-1"))
            with patch("mlflow.artifacts.download_artifacts", side_effect=download):
                self.assertEqual(restore(Namespace(**vars(arguments), checkpoint="checkpoint-1")), 0)
        self.assertEqual((partial / "trainer_state.json").read_text(), "archived")
        self.assertEqual(list(self.output.glob(".restore-*")), [])

    def test_retry_archives_failed_save_before_retention_can_remove_it(self):
        dataset = [{"input_ids": torch.tensor([1.0, 2.0]), "labels": torch.tensor([0.5])}]
        with mlflow.start_run() as parent:
            self.run.mkdir(parents=True)
            (self.run / "mlflow-run-id").write_text(parent.info.run_id)
            with mlflow.start_run(nested=True):
                trainer = Trainer(
                    model=TinyModel(), args=self.arguments(self.output),
                    train_dataset=dataset, callbacks=[RecoverCheckpointArchives()],
                )
                with self.fail_third_upload():
                    with self.assertRaisesRegex(OSError, "artifact store unavailable"):
                        trainer.train()
            self.assertNotIn("checkpoint-3", archived_checkpoints(self.run))

            # Failed recovery must stop before a new save can rotate local files.
            with mlflow.start_run(nested=True):
                retry = Trainer(
                    model=TinyModel(), args=self.arguments(self.output),
                    train_dataset=dataset, callbacks=[RecoverCheckpointArchives()],
                )
                with patch("checkpoints.mlflow.pyfunc.log_model", side_effect=OSError("still offline")):
                    with self.assertRaisesRegex(OSError, "still offline"):
                        retry.train(resume_from_checkpoint=str(self.output / "checkpoint-3"))
            self.assertTrue((self.output / "checkpoint-3").is_dir())
            self.assertFalse((self.output / "checkpoint-4").exists())

            with mlflow.start_run(nested=True):
                arguments = self.arguments(self.output)
                arguments.max_steps = 5
                resumed = Trainer(
                    model=TinyModel(), args=arguments, train_dataset=dataset,
                    callbacks=[RecoverCheckpointArchives()],
                )
                resumed.train(resume_from_checkpoint=str(self.output / "checkpoint-3"))
            self.assertFalse((self.output / "checkpoint-3").exists())
            self.assertEqual(set(archived_checkpoints(self.run)), {
                f"checkpoint-{step}" for step in range(1, 6)
            })
            # The archive uploaded by recovery restores like a native one.
            self.assertEqual(
                resolve_checkpoint(self.output, "checkpoint-3"), self.output / "checkpoint-3",
            )

    def test_concurrent_restores_share_one_download_and_clear_stale_staging(self):
        self.output.mkdir(parents=True)
        staging = self.output / ".restore-checkpoint-7"
        staging.mkdir()
        (staging / "abandoned").write_bytes(b"partial")
        entered, release = Event(), Event()

        def download(*, artifact_uri, dst_path):
            self.assertFalse((Path(dst_path) / "abandoned").exists())
            restored = Path(dst_path) / "model" / "artifacts" / "checkpoint-7"
            restored.mkdir(parents=True)
            for name in (*REQUIRED_CHECKPOINT_FILES, "model.safetensors"):
                (restored / name).touch()
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test did not release download")
            return restored.parent.parent

        archives = {"checkpoint-7": "fixture-model"}
        with patch("mlflow.artifacts.download_artifacts", side_effect=download) as mocked:
            with ThreadPoolExecutor(max_workers=2) as workers:
                first = workers.submit(resolve_checkpoint, self.output, "checkpoint-7", archives=archives)
                self.assertTrue(entered.wait(timeout=5))
                second = workers.submit(resolve_checkpoint, self.output, "checkpoint-7", archives=archives)
                release.set()
                self.assertEqual(first.result(timeout=5), second.result(timeout=5))
            self.assertEqual(mocked.call_count, 1)
        self.assertFalse(staging.exists())


if __name__ == "__main__":
    unittest.main()

"""Exercise native Trainer saves, MLflow artifacts and recovery after rotation."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import mlflow
from mlflow.store.artifact.local_artifact_repo import LocalArtifactRepository
from safetensors.torch import load_file
import torch
from transformers import Trainer, TrainerCallback, TrainingArguments

TRAINING = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING))
from checkpoints import archived_checkpoints, resolve_checkpoint  # noqa: E402
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

    def test_native_archives_preserve_pruned_checkpoint_and_full_resume_state(self):
        snapshots = {}

        class CaptureSaves(TrainerCallback):
            def on_save(self, args, state, control, **kwargs):
                directory = Path(args.output_dir) / f"checkpoint-{state.global_step}"
                snapshots[directory.name] = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in directory.iterdir() if path.is_file()
                }

        native_upload = LocalArtifactRepository.log_artifacts
        uploads = 0

        def fail_third_upload(repository, local_dir, artifact_path=None):
            nonlocal uploads
            if (Path(local_dir) / "MLmodel").is_file():
                uploads += 1
                if uploads == 3:
                    raise OSError("artifact store unavailable")
            return native_upload(repository, local_dir, artifact_path)

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
                with patch.object(LocalArtifactRepository, "log_artifacts", fail_third_upload):
                    trainer.train()

        self.assertEqual(uploads, 3)
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
        self.assertEqual(list(self.output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

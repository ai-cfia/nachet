"""Exercise recovery of a failed MLflow checkpoint upload on a real Trainer."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import mlflow
from mlflow.store.artifact.local_artifact_repo import LocalArtifactRepository
import torch
from transformers import Trainer, TrainingArguments

TRAINING = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRAINING))
from checkpoints import RecoverCheckpointArchives, archived_checkpoints  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

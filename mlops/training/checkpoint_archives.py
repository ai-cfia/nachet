"""Recover LOCAL_ONLY checkpoints before Trainer can rotate their local files."""

import logging
import os
from pathlib import Path

import mlflow
from transformers import TrainerCallback
from transformers.utils import ENV_VARS_TRUE_VALUES

from checkpoints import archived_checkpoints, list_complete_checkpoints

logger = logging.getLogger(__name__)


class RecoverCheckpointArchives(TrainerCallback):
    """LOCAL_ONLY -> MLflow READY -> eligible for Trainer's normal retention.

    Native MLflow on_save owns new uploads. This callback runs after its setup
    and recovers interrupted uploads before a retry can save or rotate again.
    An upload error stops training, leaving the complete local checkpoint.
    """

    def on_train_begin(self, args, state, control, **kwargs):
        if (
            not state.is_world_process_zero
            or "mlflow" not in args.report_to
            or os.getenv("HF_MLFLOW_LOG_ARTIFACTS", "").upper() not in ENV_VARS_TRUE_VALUES
        ):
            return
        output = Path(args.output_dir)
        checkpoints = list_complete_checkpoints(output) if output.is_dir() else []
        if not checkpoints:
            return
        archives = archived_checkpoints(output.parent)
        for checkpoint in checkpoints:
            if checkpoint.name not in archives:
                logger.info("Recovering checkpoint archive: %s", checkpoint.name)
                mlflow.pyfunc.log_model(
                    name=checkpoint.name,
                    artifacts={"model_path": str(checkpoint)},
                    python_model=mlflow.pyfunc.PythonModel(),
                )

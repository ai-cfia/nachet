"""Run lifecycle shared by detector and classifier launchers."""

from __future__ import annotations

import argparse
import contextlib
import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from urllib.parse import quote

from checkpoints import (
    CHECKPOINT_PATTERN,
    checkpoint_is_complete,
    list_complete_checkpoints,
)

if TYPE_CHECKING:
    from mlflow import MlflowClient


def required_environment_value(name: str) -> str:
    """Return a required, non-empty environment value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"required environment variable is not set: {name}")
    return value


def resolve_resume_checkpoint(
    runs_root: Path,
    resume_run_id: str | None,
    resume_checkpoint: str,
) -> tuple[Path | None, str | None]:
    if resume_run_id is None:
        return None, None

    source_run = runs_root / resume_run_id
    trainer_output = source_run / "trainer-output"
    if not trainer_output.is_dir():
        raise FileNotFoundError(f"training output does not exist: {trainer_output}")

    if resume_checkpoint == "latest":
        checkpoints = list_complete_checkpoints(trainer_output)
        if not checkpoints:
            raise FileNotFoundError(
                f"no checkpoints are available in resumed run {resume_run_id}"
            )
        checkpoint_path = checkpoints[-1]
    else:
        if CHECKPOINT_PATTERN.fullmatch(resume_checkpoint) is None:
            raise ValueError("resume-checkpoint must be latest or checkpoint-<step>")
        checkpoint_path = trainer_output / resume_checkpoint

    if not checkpoint_is_complete(checkpoint_path):
        raise ValueError(f"checkpoint is incomplete: {checkpoint_path.name}")

    mlflow_run_id = read_mlflow_run_id(source_run)
    if mlflow_run_id is None:
        raise FileNotFoundError(
            f"MLflow run ID does not exist for resumed run {resume_run_id}"
        )
    return checkpoint_path, mlflow_run_id


def read_mlflow_run_id(run_root: Path) -> str | None:
    path = run_root / "mlflow-run-id"
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"MLflow run ID is not a file: {path}")
    run_id = path.read_text(encoding="utf-8").strip()
    if not run_id:
        raise ValueError(f"MLflow run ID is empty: {path}")
    return run_id


def run_succeeded(run_root: Path) -> bool:
    path = run_root / "exit-code"
    if not path.exists():
        return False
    if not path.is_file():
        raise ValueError(f"exit code is not a file: {path}")
    try:
        return int(path.read_text(encoding="utf-8").strip()) == 0
    except ValueError as error:
        raise ValueError(f"exit code is invalid: {path}") from error


def remove_incomplete_checkpoints(output_path: Path) -> None:
    if not output_path.is_dir():
        return

    # A failed save can leave an unusable checkpoint directory. Remove only
    # incomplete checkpoints so the trainer can safely write them again.
    for path in output_path.iterdir():
        if (
            path.is_dir()
            and CHECKPOINT_PATTERN.fullmatch(path.name) is not None
            and not checkpoint_is_complete(path)
        ):
            shutil.rmtree(path)


def run_and_tee(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    log_path: Path,
) -> int:
    has_previous_output = log_path.exists() and log_path.stat().st_size > 0
    with log_path.open("a", encoding="utf-8") as log_handle:
        if has_previous_output:
            log_handle.write("\n--- retry ---\n")
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # The wrapper is PID 1, so it passes termination signals to the trainer.
        previous_handlers: dict[signal.Signals, signal.Handlers] = {}

        def forward_signal(signum: int, _frame: object) -> None:
            if process.poll() is None:
                process.send_signal(signum)

        for forwarded_signal in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[forwarded_signal] = signal.getsignal(forwarded_signal)
            signal.signal(forwarded_signal, forward_signal)

        try:
            if process.stdout is None:
                raise RuntimeError("training process did not expose its output stream")
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log_handle.write(line)
                log_handle.flush()
            return process.wait()
        finally:
            for forwarded_signal, previous_handler in previous_handlers.items():
                signal.signal(forwarded_signal, previous_handler)


def validate_runtime() -> None:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the training pod")


def get_or_create_mlflow_run(
    run_name: str,
    existing_run_id: str | None,
) -> tuple[MlflowClient, str]:
    import mlflow

    client = mlflow.MlflowClient()
    if existing_run_id is None:
        experiment = mlflow.set_experiment(
            required_environment_value("MLFLOW_EXPERIMENT_NAME")
        )
        run = client.create_run(
            experiment.experiment_id,
            tags={"mlflow.runName": run_name},
        )
        run_id = run.info.run_id
    else:
        client.get_run(existing_run_id)
        run_id = existing_run_id
    return client, run_id


def build_mlflow_run_url(
    public_url: str,
    experiment_id: str,
    run_id: str,
) -> str:
    base_url = public_url.rstrip("/")
    return (
        f"{base_url}/#/experiments/{quote(experiment_id, safe='')}"
        f"/runs/{quote(run_id, safe='')}"
    )


# Each launcher supplies its command; this module owns retries and MLflow identity.
def execute_training(
    args: argparse.Namespace,
    command_for_resume: Callable[[Path | None], list[str]],
    input_artifacts: tuple[Path, ...] = (),
) -> int:
    run_root = args.runs_root / args.run_id
    output_path = run_root / "trainer-output"
    if run_root.exists() and not run_root.is_dir():
        raise ValueError(f"run path is not a directory: {run_root}")
    retrying = run_root.is_dir()
    if retrying and run_succeeded(run_root):
        return 0

    requested_resume_run_id = (
        None if args.resume_run_id in (None, "", "none") else args.resume_run_id
    )
    if retrying:
        checkpoints = (
            list_complete_checkpoints(output_path) if output_path.is_dir() else []
        )
        resume_checkpoint = checkpoints[-1] if checkpoints else None
        existing_mlflow_run_id = read_mlflow_run_id(run_root)

        # Prefer progress from this attempt. If it failed before saving a new
        # checkpoint, retry from the checkpoint the run originally received.
        if resume_checkpoint is None and requested_resume_run_id is not None:
            resume_checkpoint, resumed_mlflow_run_id = resolve_resume_checkpoint(
                args.resume_runs_root or args.runs_root,
                requested_resume_run_id,
                args.resume_checkpoint,
            )
            if (
                existing_mlflow_run_id is not None
                and existing_mlflow_run_id != resumed_mlflow_run_id
            ):
                raise ValueError(
                    "retry and resumed checkpoint refer to different MLflow runs"
                )
            existing_mlflow_run_id = resumed_mlflow_run_id
    else:
        resume_checkpoint, existing_mlflow_run_id = resolve_resume_checkpoint(
            args.resume_runs_root or args.runs_root,
            requested_resume_run_id,
            args.resume_checkpoint,
        )
    command = command_for_resume(resume_checkpoint)

    if args.dry_run:
        print(shlex.join(command))
        return 0

    mlflow_public_url = required_environment_value("MLFLOW_PUBLIC_URL")
    mlflow_client = None
    mlflow_run_id = None
    try:
        validate_runtime()
        run_root.mkdir(parents=True, exist_ok=True)
        output_path.mkdir(exist_ok=True)
        remove_incomplete_checkpoints(output_path)
        (run_root / "exit-code").unlink(missing_ok=True)
        mlflow_client, mlflow_run_id = get_or_create_mlflow_run(
            args.run_id,
            existing_mlflow_run_id,
        )
        # Persist the MLflow identity before training so retries reuse the run.
        (run_root / "mlflow-run-id").write_text(
            f"{mlflow_run_id}\n",
            encoding="utf-8",
        )
        for artifact in input_artifacts:
            mlflow_client.log_artifact(
                mlflow_run_id, str(artifact), artifact_path="inputs"
            )
        mlflow_experiment_id = str(
            mlflow_client.get_run(mlflow_run_id).info.experiment_id
        )
        mlflow_run_url = build_mlflow_run_url(
            mlflow_public_url,
            mlflow_experiment_id,
            mlflow_run_id,
        )
        (run_root / "mlflow-run-url").write_text(
            f"{mlflow_run_url}\n",
            encoding="utf-8",
        )

        environment = os.environ.copy()
        environment["MLFLOW_RUN_ID"] = mlflow_run_id
        environment["HF_MLFLOW_LOG_ARTIFACTS"] = "TRUE"
        return_code = run_and_tee(
            command,
            args.dataset_root,
            environment,
            run_root / "train_log.txt",
        )
        mlflow_client.set_terminated(
            mlflow_run_id,
            status="FINISHED" if return_code == 0 else "FAILED",
        )
        # Write the exit code last so only a finished attempt is marked successful.
        (run_root / "exit-code").write_text(
            f"{return_code}\n",
            encoding="utf-8",
        )
        return return_code
    except Exception:
        if mlflow_client is not None and mlflow_run_id is not None:
            with contextlib.suppress(Exception):
                mlflow_client.set_terminated(mlflow_run_id, status="FAILED")
        raise

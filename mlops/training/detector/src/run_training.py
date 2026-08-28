"""Run Nachet detector training and record its MLflow status."""

from __future__ import annotations

import argparse
import contextlib
import os
import shlex
import signal
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from checkpoints import (
    CHECKPOINT_PATTERN,
    checkpoint_is_complete,
    list_complete_checkpoints,
)

if TYPE_CHECKING:
    from mlflow import MlflowClient


@dataclass(frozen=True)
class RunProfile:
    epochs: int
    image_size: int
    batch_size: int
    gradient_accumulation_steps: int
    max_train_samples: int | None
    max_eval_samples: int | None
    warmup_steps: int
    learning_rate: float
    seed: int


RUN_PROFILES = {
    "smoke": RunProfile(
        epochs=1,
        image_size=640,
        batch_size=2,
        gradient_accumulation_steps=1,
        max_train_samples=32,
        max_eval_samples=16,
        warmup_steps=0,
        learning_rate=0.00001,
        seed=2438,
    ),
    "full": RunProfile(
        epochs=50,
        image_size=640,
        batch_size=24,
        gradient_accumulation_steps=1,
        max_train_samples=None,
        max_eval_samples=None,
        warmup_steps=760,
        learning_rate=0.00001,
        seed=2438,
    ),
}


def profile_int(value: str) -> int | None:
    if value == "profile-default":
        return None
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def profile_nonnegative_int(value: str) -> int | None:
    if value == "profile-default":
        return None
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def profile_float(value: str) -> float | None:
    if value == "profile-default":
        return None
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def effective_run_profile(
    profile: RunProfile,
    args: argparse.Namespace,
) -> RunProfile:
    overrides = {}
    for name in (
        "epochs",
        "image_size",
        "batch_size",
        "gradient_accumulation_steps",
        "warmup_steps",
        "learning_rate",
        "seed",
    ):
        value = getattr(args, name)
        if value is not None:
            overrides[name] = value
    return replace(profile, **overrides)


def decimal_text(value: float) -> str:
    return format(value, ".15f").rstrip("0").rstrip(".")


def input_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def build_command(
    trainer_path: Path,
    dataset_config: Path,
    model_path: Path,
    output_path: Path,
    profile: RunProfile,
    resume_checkpoint: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(trainer_path),
        "--do_train",
        "--do_eval",
        "--dataset_config",
        str(dataset_config),
        "--train_val_split",
        "0.15",
        "--output_dir",
        str(output_path),
        "--num_train_epochs",
        str(profile.epochs),
        "--image_square_size",
        str(profile.image_size),
        "--per_device_train_batch_size",
        str(profile.batch_size),
        "--dataloader_num_workers",
        "0",
        "--gradient_accumulation_steps",
        str(profile.gradient_accumulation_steps),
        "--warmup_steps",
        str(profile.warmup_steps),
        "--learning_rate",
        decimal_text(profile.learning_rate),
        "--seed",
        str(profile.seed),
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
        str(profile.epochs),
        "--bf16",
        "--ignore_mismatched_sizes",
        "--remove_unused_columns",
        "false",
        "--eval_do_concat_batches",
        "false",
        "--model_name_or_path",
        str(model_path),
    ]
    if profile.max_train_samples is not None:
        command.extend(["--max_train_samples", str(profile.max_train_samples)])
    if profile.max_eval_samples is not None:
        command.extend(["--max_eval_samples", str(profile.max_eval_samples)])
    if resume_checkpoint is not None:
        command.extend(["--resume_from_checkpoint", str(resume_checkpoint)])
    return command


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

    mlflow_run_id_path = source_run / "mlflow-run-id"
    if not mlflow_run_id_path.is_file():
        raise FileNotFoundError(
            f"MLflow run ID does not exist for resumed run {resume_run_id}"
        )
    mlflow_run_id = mlflow_run_id_path.read_text(encoding="utf-8").strip()
    if not mlflow_run_id:
        raise ValueError(f"resumed run {resume_run_id} has an empty MLflow run ID")
    return checkpoint_path, mlflow_run_id


def run_and_tee(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    log_path: Path,
) -> int:
    with log_path.open("w", encoding="utf-8") as log_handle:
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


def open_mlflow_run(
    run_name: str,
    dataset_config: Path,
    existing_run_id: str | None,
) -> tuple[MlflowClient, str]:
    import mlflow

    client = mlflow.MlflowClient()
    if existing_run_id is None:
        experiment = mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT_NAME"])
        run = client.create_run(
            experiment.experiment_id,
            tags={"mlflow.runName": run_name},
        )
        run_id = run.info.run_id
    else:
        client.get_run(existing_run_id)
        run_id = existing_run_id

    try:
        client.log_artifact(run_id, str(dataset_config), artifact_path="inputs")
    except Exception:
        with contextlib.suppress(Exception):
            client.set_terminated(run_id, status="FAILED")
        raise
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("/inputs"),
        help="working directory containing the prepared dataset",
    )
    parser.add_argument(
        "--dataset-config",
        type=Path,
        required=True,
        help="dataset configuration path, relative to --dataset-root or absolute",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        required=True,
        help="base model path, relative to --dataset-root or absolute",
    )
    parser.add_argument(
        "--run-profile",
        choices=sorted(RUN_PROFILES),
        required=True,
        help="training parameter set",
    )
    parser.add_argument("--epochs", type=profile_int, default=None)
    parser.add_argument("--image-size", type=profile_int, default=None)
    parser.add_argument("--batch-size", type=profile_int, default=None)
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=profile_int,
        default=None,
    )
    parser.add_argument(
        "--warmup-steps",
        type=profile_nonnegative_int,
        default=None,
    )
    parser.add_argument("--learning-rate", type=profile_float, default=None)
    parser.add_argument("--seed", type=profile_nonnegative_int, default=None)
    parser.add_argument(
        "--run-id",
        required=True,
        help="identifier used as the output directory name",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("/runs"),
        help="root of the training output directory",
    )
    parser.add_argument(
        "--resume-runs-root",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--resume-run-id",
        default=None,
        help="earlier training run whose checkpoint and MLflow run should resume",
    )
    parser.add_argument(
        "--resume-checkpoint",
        default="latest",
        help="checkpoint-<step> below --resume-run-id, or latest",
    )
    parser.add_argument(
        "--trainer-path",
        type=Path,
        default=Path(__file__).with_name("train_detector.py"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate local inputs and print the training command",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_profile = effective_run_profile(RUN_PROFILES[args.run_profile], args)
    dataset_config = input_path(args.dataset_root, args.dataset_config)
    model_path = input_path(args.dataset_root, args.model_path)
    run_root = args.runs_root / args.run_id
    output_path = run_root / "trainer-output"

    if not args.dataset_root.is_dir():
        raise FileNotFoundError(f"dataset root does not exist: {args.dataset_root}")
    if not dataset_config.is_file():
        raise FileNotFoundError(
            f"dataset configuration does not exist: {dataset_config}"
        )
    if not model_path.is_dir():
        raise FileNotFoundError(f"base model does not exist: {model_path}")
    if not args.trainer_path.is_file():
        raise FileNotFoundError(f"trainer does not exist: {args.trainer_path}")

    resume_run_id = (
        None if args.resume_run_id in (None, "", "none") else args.resume_run_id
    )
    resume_checkpoint, existing_mlflow_run_id = resolve_resume_checkpoint(
        args.resume_runs_root or args.runs_root,
        resume_run_id,
        args.resume_checkpoint,
    )
    command = build_command(
        args.trainer_path,
        dataset_config,
        model_path,
        output_path,
        run_profile,
        resume_checkpoint,
    )

    if args.dry_run:
        print(shlex.join(command))
        return 0

    mlflow_client = None
    mlflow_run_id = None
    try:
        validate_runtime()
        run_root.mkdir(parents=True, exist_ok=False)
        output_path.mkdir()
        mlflow_client, mlflow_run_id = open_mlflow_run(
            args.run_id,
            dataset_config,
            existing_mlflow_run_id,
        )
        mlflow_experiment_id = str(
            mlflow_client.get_run(mlflow_run_id).info.experiment_id
        )
        mlflow_run_url = build_mlflow_run_url(
            os.environ["MLFLOW_PUBLIC_URL"],
            mlflow_experiment_id,
            mlflow_run_id,
        )
        (run_root / "mlflow-run-id").write_text(
            f"{mlflow_run_id}\n",
            encoding="utf-8",
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
        (run_root / "exit-code").write_text(
            f"{return_code}\n",
            encoding="utf-8",
        )
        mlflow_client.set_terminated(
            mlflow_run_id,
            status="FINISHED" if return_code == 0 else "FAILED",
        )
        return return_code
    except Exception:
        if mlflow_client is not None and mlflow_run_id is not None:
            with contextlib.suppress(Exception):
                mlflow_client.set_terminated(mlflow_run_id, status="FAILED")
        raise


if __name__ == "__main__":
    raise SystemExit(main())

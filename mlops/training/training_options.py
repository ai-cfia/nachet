"""Command-line options shared by the detector and classifier launchers."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path


@dataclass(frozen=True)
class RunProfile:
    epochs: int
    checkpoint_retention: int
    batch_size: int
    gradient_accumulation_steps: int
    max_train_samples: int | None
    max_eval_samples: int | None
    warmup_steps: int
    learning_rate: float
    seed: int


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


# Only explicit CLI overrides replace a profile's defaults.
def effective_run_profile(
    profile: RunProfile,
    args: argparse.Namespace,
) -> RunProfile:
    overrides = {}
    for field in fields(profile):
        name = field.name
        value = getattr(args, name, None)
        if value is not None:
            overrides[name] = value
    return replace(profile, **overrides)


def input_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


# Dataset arguments stay with each launcher; these options control training.
def build_training_command(
    trainer_path: Path,
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
        "--output_dir",
        str(output_path),
        "--num_train_epochs",
        str(profile.epochs),
        "--per_device_train_batch_size",
        str(profile.batch_size),
        "--dataloader_num_workers",
        "0",
        "--gradient_accumulation_steps",
        str(profile.gradient_accumulation_steps),
        "--warmup_steps",
        str(profile.warmup_steps),
        "--learning_rate",
        str(profile.learning_rate),
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
        str(profile.checkpoint_retention),
        "--bf16",
        "--ignore_mismatched_sizes",
        "--remove_unused_columns",
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


def training_parser(
    description: str, profiles: dict[str, RunProfile], trainer_path: Path
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("/inputs"),
        help="working directory containing the prepared dataset",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        required=True,
        help="base model path, relative to --dataset-root or absolute",
    )
    parser.add_argument(
        "--run-profile",
        choices=sorted(profiles),
        required=True,
        help="training parameter set",
    )
    parser.add_argument("--epochs", type=profile_int, default=None)
    parser.add_argument("--checkpoint-retention", type=profile_int, default=None)
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
        default=trainer_path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate local inputs and print the training command",
    )
    return parser

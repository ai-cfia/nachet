"""Run Nachet classifier training and record its MLflow status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Resolve shared training code both in the checkout and in the image.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from training_runtime import execute_training  # noqa: E402
from training_options import (  # noqa: E402
    RunProfile,
    build_training_command,
    effective_run_profile,
    input_path,
    training_parser,
)


RUN_PROFILES = {
    "smoke": RunProfile(
        epochs=1,
        checkpoint_retention=1,
        batch_size=2,
        gradient_accumulation_steps=1,
        max_train_samples=32,
        max_eval_samples=16,
        warmup_steps=0,
        learning_rate=0.000007,
        seed=2438,
    ),
    "full": RunProfile(
        epochs=50,
        checkpoint_retention=50,
        batch_size=80,
        gradient_accumulation_steps=1,
        max_train_samples=None,
        max_eval_samples=None,
        warmup_steps=1000,
        learning_rate=0.000007,
        seed=2438,
    ),
}


def build_command(
    trainer_path: Path,
    train_dir: Path,
    model_path: Path,
    output_path: Path,
    profile: RunProfile,
    resume_checkpoint: Path | None = None,
    validation_dir: Path | None = None,
) -> list[str]:
    command = build_training_command(
        trainer_path, model_path, output_path, profile, resume_checkpoint
    )
    command.extend(["--train_dir", str(train_dir), "--train_val_split", "0.15"])
    if validation_dir is not None:
        command.extend(["--validation_dir", str(validation_dir)])
    return command


def parse_args() -> argparse.Namespace:
    parser = training_parser(
        __doc__, RUN_PROFILES, Path(__file__).with_name("train_classifier.py")
    )
    parser.add_argument(
        "--train-dir",
        type=Path,
        required=True,
        help="species-labelled image directory, relative to --dataset-root or absolute",
    )
    parser.add_argument(
        "--validation-dir",
        default="none",
        help="optional held-out directory, or none to split training data",
    )
    args = parser.parse_args()
    # An empty Path means the dataset root, not an omitted validation directory.
    if not args.validation_dir.strip():
        parser.error("--validation-dir must be a directory or none")
    return args


def main() -> int:
    args = parse_args()
    run_profile = effective_run_profile(RUN_PROFILES[args.run_profile], args)
    train_dir = input_path(args.dataset_root, args.train_dir)
    validation_dir = (
        None
        if args.validation_dir == "none"
        else input_path(args.dataset_root, Path(args.validation_dir))
    )
    model_path = input_path(args.dataset_root, args.model_path)

    if not args.dataset_root.is_dir():
        raise FileNotFoundError(f"dataset root does not exist: {args.dataset_root}")
    if not train_dir.is_dir():
        raise FileNotFoundError(f"training directory does not exist: {train_dir}")
    if validation_dir is not None and not validation_dir.is_dir():
        raise FileNotFoundError(
            f"validation directory does not exist: {validation_dir}"
        )
    if not model_path.is_dir():
        raise FileNotFoundError(f"base model does not exist: {model_path}")
    if not args.trainer_path.is_file():
        raise FileNotFoundError(f"trainer does not exist: {args.trainer_path}")

    def command_for_resume(output_path: Path, checkpoint: Path | None) -> list[str]:
        return build_command(
            args.trainer_path,
            train_dir,
            model_path,
            output_path,
            run_profile,
            checkpoint,
            validation_dir,
        )

    return execute_training(args, command_for_resume)


if __name__ == "__main__":
    raise SystemExit(main())

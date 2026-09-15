"""Run Nachet detector training and record its MLflow status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Resolve shared training code both in the checkout and in the image.
training_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(training_root))
from training_runtime import execute_training  # noqa: E402
from training_options import (  # noqa: E402
    RunProfile,
    build_training_command,
    effective_run_profile,
    input_path,
    training_parser,
    profile_int,
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
        learning_rate=0.00001,
        seed=2438,
    ),
    "full": RunProfile(
        epochs=50,
        checkpoint_retention=50,
        batch_size=24,
        gradient_accumulation_steps=1,
        max_train_samples=None,
        max_eval_samples=None,
        warmup_steps=760,
        learning_rate=0.00001,
        seed=2438,
    ),
}


def build_command(
    trainer_path: Path,
    dataset_config: Path,
    model_path: Path,
    output_path: Path,
    profile: RunProfile,
    resume_checkpoint: Path | None = None,
    image_size: int | None = None,
) -> list[str]:
    command = build_training_command(
        trainer_path, model_path, output_path, profile, resume_checkpoint
    )
    command.extend(
        [
            "--dataset_config",
            str(dataset_config),
            "--train_val_split",
            "0.15",
            "--image_square_size",
            str(640 if image_size is None else image_size),
            "--eval_do_concat_batches",
            "false",
        ]
    )
    return command


def parse_args() -> argparse.Namespace:
    parser = training_parser(
        __doc__, RUN_PROFILES, Path(__file__).with_name("train_detector.py")
    )
    parser.add_argument(
        "--dataset-config",
        type=Path,
        required=True,
        help="dataset configuration path, relative to --dataset-root or absolute",
    )
    parser.add_argument("--image-size", type=profile_int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_profile = effective_run_profile(RUN_PROFILES[args.run_profile], args)
    dataset_config = input_path(args.dataset_root, args.dataset_config)
    model_path = input_path(args.dataset_root, args.model_path)

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

    def command_for_resume(output_path: Path, checkpoint: Path | None) -> list[str]:
        return build_command(
            args.trainer_path,
            dataset_config,
            model_path,
            output_path,
            run_profile,
            checkpoint,
            args.image_size,
        )

    return execute_training(args, command_for_resume, (dataset_config,))


if __name__ == "__main__":
    raise SystemExit(main())

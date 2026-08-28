"""List completed training checkpoints and validate the reviewer's selection."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CHECKPOINT_PATTERN = re.compile(r"^checkpoint-([1-9][0-9]*)$")
REQUIRED_CHECKPOINT_FILES = (
    "optimizer.pt",
    "rng_state.pth",
    "scheduler.pt",
    "trainer_state.json",
    "training_args.bin",
)
MODEL_WEIGHT_FILES = (
    "model.safetensors",
    "pytorch_model.bin",
)


def checkpoint_is_complete(path: Path) -> bool:
    """Return whether a checkpoint contains the state needed to resume."""
    if not path.is_dir():
        return False

    if any(not (path / name).is_file() for name in REQUIRED_CHECKPOINT_FILES):
        return False

    return any((path / name).is_file() for name in MODEL_WEIGHT_FILES)


def list_complete_checkpoints(trainer_output: Path) -> list[Path]:
    """Return complete checkpoints ordered by training step."""
    checkpoints = []
    for path in trainer_output.iterdir():
        match = CHECKPOINT_PATTERN.fullmatch(path.name)
        if match is not None and checkpoint_is_complete(path):
            checkpoints.append((int(match.group(1)), path))
    return [path for _step, path in sorted(checkpoints)]


def resolve_trainer_output(runs_root: Path, run_id: str) -> Path:
    trainer_output = runs_root / run_id / "trainer-output"
    if not trainer_output.is_dir():
        raise FileNotFoundError(f"training output does not exist: {trainer_output}")
    return trainer_output


def list_checkpoints(trainer_output: Path) -> list[str]:
    checkpoints = list_complete_checkpoints(trainer_output)
    if not checkpoints:
        raise FileNotFoundError("training completed without a checkpoint directory")
    return [path.name for path in checkpoints]


def parse_checkpoint_options(value: str) -> list[str]:
    try:
        options = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("checkpoint options must be valid JSON") from error
    candidates = options.get("enum") if isinstance(options, dict) else None
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("checkpoint options must contain a non-empty enum list")
    if any(not isinstance(item, str) for item in candidates):
        raise ValueError("checkpoint option names must be strings")
    if len(candidates) != len(set(candidates)):
        raise ValueError("checkpoint option names must be unique")
    if any(CHECKPOINT_PATTERN.fullmatch(item) is None for item in candidates):
        raise ValueError("checkpoint options contain an invalid name")
    return candidates


def write_options(args: argparse.Namespace) -> int:
    trainer_output = resolve_trainer_output(args.runs_root, args.run_id)
    options = {"enum": list_checkpoints(trainer_output)}
    args.output.write_text(json.dumps(options) + "\n", encoding="utf-8")
    print(json.dumps(options))
    return 0


def validate_selection(args: argparse.Namespace) -> int:
    available = parse_checkpoint_options(args.checkpoint_options)
    selected = args.selected_checkpoint.strip()
    if selected not in available:
        raise ValueError(f"unknown checkpoint selection: {selected}")

    # Recheck after the pause in case the checkpoint changed.
    trainer_output = resolve_trainer_output(args.runs_root, args.run_id)
    selected_path = trainer_output / selected
    if not checkpoint_is_complete(selected_path):
        raise ValueError(f"checkpoint is no longer complete: {selected}")

    args.output.write_text(f"{selected}\n", encoding="utf-8")
    print(json.dumps({"selected_checkpoint": selected}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=Path("/runs"))
    parser.add_argument("--run-id", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--output", type=Path, required=True)
    list_parser.set_defaults(handler=write_options)

    validate_parser = subparsers.add_parser("validate-selection")
    validate_parser.add_argument("--checkpoint-options", required=True)
    validate_parser.add_argument("--selected-checkpoint", required=True)
    validate_parser.add_argument("--output", type=Path, required=True)
    validate_parser.set_defaults(handler=validate_selection)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

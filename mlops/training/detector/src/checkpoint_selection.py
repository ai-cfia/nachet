"""List completed training checkpoints and validate the reviewer's selection."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from checkpoint_state import (
    CHECKPOINT_PATTERN,
    checkpoint_is_complete,
    list_complete_checkpoints,
)


RUN_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def contained_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    resolved_path = (resolved_root / relative_path).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"path leaves its approved root: {relative_path}")
    return resolved_path


def resolve_trainer_output(runs_root: Path, run_id: str) -> Path:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run-id must be a lowercase Kubernetes-style name")
    trainer_output = contained_path(runs_root, f"{run_id}/trainer-output")
    if not trainer_output.is_dir() or trainer_output.is_symlink():
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

    # Recheck shared storage after the pause in case the checkpoint changed.
    trainer_output = resolve_trainer_output(args.runs_root, args.run_id)
    selected_path = contained_path(trainer_output, selected)
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

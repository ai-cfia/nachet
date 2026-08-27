"""Recognize detector checkpoints that contain complete resume state."""

from __future__ import annotations

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
    """Return whether a checkpoint has the local state required for resumption."""
    if not path.is_dir() or path.is_symlink():
        return False

    required_files = [path / name for name in REQUIRED_CHECKPOINT_FILES]
    if any(not file.is_file() or file.is_symlink() for file in required_files):
        return False

    return any(
        file.is_file() and not file.is_symlink()
        for file in (path / name for name in MODEL_WEIGHT_FILES)
    )


def list_complete_checkpoints(trainer_output: Path) -> list[Path]:
    """Return complete checkpoints ordered by training step."""
    checkpoints = []
    for path in trainer_output.iterdir():
        match = CHECKPOINT_PATTERN.fullmatch(path.name)
        if match is not None and checkpoint_is_complete(path):
            checkpoints.append((int(match.group(1)), path))
    return [path for _step, path in sorted(checkpoints)]

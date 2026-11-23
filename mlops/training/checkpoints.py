"""List checkpoints with the expected resume files and validate a selection."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from enum import Enum
import json
import re
import shutil
from pathlib import Path

from filelock import FileLock

CHECKPOINT_PATTERN = re.compile(r"^checkpoint-([1-9][0-9]*)$")
MAX_CHECKPOINT_SELECTIONS = 3
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


class UnarchivedIncompleteCheckpoint(ValueError):
    """A partial local checkpoint has no MLflow archive to restore from."""


class LocalCheckpointState(Enum):
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"


def checkpoint_state(path: Path) -> LocalCheckpointState:
    """Derive local state from files; MLflow owns the separate archive state."""
    if not path.exists():
        return LocalCheckpointState.MISSING
    if not path.is_dir():
        return LocalCheckpointState.INCOMPLETE

    if any(not (path / name).is_file() for name in REQUIRED_CHECKPOINT_FILES):
        return LocalCheckpointState.INCOMPLETE

    if any((path / name).is_file() for name in MODEL_WEIGHT_FILES):
        return LocalCheckpointState.COMPLETE
    return LocalCheckpointState.INCOMPLETE


def checkpoint_is_complete(path: Path) -> bool:
    """Return whether the expected resume files are present."""
    return checkpoint_state(path) is LocalCheckpointState.COMPLETE


def list_complete_checkpoints(trainer_output: Path) -> list[Path]:
    """Return checkpoints with the expected resume files, ordered by step."""
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
    names = {path.name for path in list_complete_checkpoints(trainer_output)}
    names.update(archived_checkpoints(trainer_output.parent))
    if not names:
        raise FileNotFoundError("training completed without a checkpoint directory")
    return sorted(names, key=lambda name: int(name.split("-")[1]))


def archived_checkpoints(run_root: Path) -> dict[str, str]:
    """Find native MLflow checkpoint models from this workflow's attempts."""
    run_id_file = run_root / "mlflow-run-id"
    if not run_id_file.is_file():
        return {}

    from mlflow import MlflowClient
    from mlflow.entities import LoggedModelStatus

    client = MlflowClient()
    parent = client.get_run(run_id_file.read_text().strip())
    runs = [parent]
    token = None
    while True:
        page = client.search_runs(
            [parent.info.experiment_id],
            filter_string=f"tags.`mlflow.parentRunId` = '{parent.info.run_id}'",
            page_token=token,
        )
        runs.extend(page)
        token = page.token
        if not token:
            break

    # A continuation shares its parent MLflow run with the source workflow.
    # Scope archives to this workflow, allowing the PVC to have another mount root.
    sources = [
        run.info.run_id for run in runs
        if Path(run.data.params.get("output_dir", "")).parts[-2:]
        == (run_root.name, "trainer-output")
    ]
    if not sources:
        return {}
    source_ids = ", ".join(f"'{run_id}'" for run_id in sources)
    models = {}
    token = None
    while True:
        page = client.search_logged_models(
            [parent.info.experiment_id],
            filter_string=f"source_run_id IN ({source_ids})",
            page_token=token,
        )
        for model in page:
            if (
                model.status == LoggedModelStatus.READY
                and CHECKPOINT_PATTERN.fullmatch(model.name)
                and (
                    model.name not in models
                    or model.creation_timestamp > models[model.name].creation_timestamp
                )
            ):
                models[model.name] = model
        token = page.token
        if not token:
            break
    return {name: model.model_id for name, model in models.items()}


def resolve_checkpoint(
    trainer_output: Path,
    name: str,
    *,
    archives: dict[str, str] | None = None,
    download: bool = True,
) -> Path:
    """Use a local checkpoint or restore its complete MLflow archive."""
    if CHECKPOINT_PATTERN.fullmatch(name) is None:
        raise ValueError(f"invalid checkpoint name: {name}")
    checkpoint = trainer_output / name
    staging = trainer_output / f".restore-{name}"
    if checkpoint_is_complete(checkpoint) and not staging.exists():
        return checkpoint
    # One owner restores this checkpoint. After a killed owner, the next owner
    # clears its staging directory; lock files stay in place to avoid inode races.
    if download:
        trainer_output.mkdir(exist_ok=True)
    lock = FileLock(str(trainer_output / f".{name}.lock")) if download else nullcontext()
    with lock:
        if download:
            shutil.rmtree(staging, ignore_errors=True)
        state = checkpoint_state(checkpoint)
        if state is LocalCheckpointState.COMPLETE:
            return checkpoint
        if archives is None:
            archives = archived_checkpoints(trainer_output.parent)
        if name not in archives:
            if state is LocalCheckpointState.INCOMPLETE:
                raise UnarchivedIncompleteCheckpoint(f"checkpoint is incomplete: {name}")
            raise FileNotFoundError(f"checkpoint is unavailable locally or in MLflow: {name}")
        if not download:
            return checkpoint

        from mlflow.artifacts import download_artifacts

        staging.mkdir()
        try:
            model = Path(download_artifacts(
                artifact_uri=f"models:/{archives[name]}", dst_path=str(staging),
            ))
            restored = model / "artifacts" / name
            if checkpoint_state(restored) is not LocalCheckpointState.COMPLETE:
                raise ValueError(f"MLflow archive is incomplete: {name}")
            # The verified archive replaces an incomplete local copy only.
            if checkpoint.is_dir() and not checkpoint_is_complete(checkpoint):
                shutil.rmtree(checkpoint)
            restored.rename(checkpoint)
        finally:
            shutil.rmtree(staging)
    return checkpoint


def archived_checkpoints(run_root: Path) -> dict[str, str]:
    """Find native MLflow checkpoint models from this workflow's attempts."""
    run_id_file = run_root / "mlflow-run-id"
    if not run_id_file.is_file():
        return {}

    from mlflow import MlflowClient
    from mlflow.entities import LoggedModelStatus

    client = MlflowClient()
    parent = client.get_run(run_id_file.read_text().strip())
    # One child run per attempt: a workflow's retries fit in the default page.
    runs = [parent, *client.search_runs(
        [parent.info.experiment_id],
        filter_string=f"tags.`mlflow.parentRunId` = '{parent.info.run_id}'",
    )]

    # A continuation shares its parent MLflow run with the source workflow.
    # Scope archives to this workflow, allowing the PVC to have another mount root.
    sources = [
        run.info.run_id for run in runs
        if Path(run.data.params.get("output_dir", "")).parts[-2:]
        == (run_root.name, "trainer-output")
    ]
    if not sources:
        return {}
    source_ids = ", ".join(f"'{run_id}'" for run_id in sources)
    models = {}
    token = None
    while True:
        page = client.search_logged_models(
            [parent.info.experiment_id],
            filter_string=f"source_run_id IN ({source_ids})",
            page_token=token,
        )
        for model in page:
            if (
                model.status == LoggedModelStatus.READY
                and CHECKPOINT_PATTERN.fullmatch(model.name)
                and (
                    model.name not in models
                    or model.creation_timestamp > models[model.name].creation_timestamp
                )
            ):
                models[model.name] = model
        token = page.token
        if not token:
            break
    return {name: model.model_id for name, model in models.items()}


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
    # Optional dropdowns include none so users can leave them unused.
    if args.optional_output is not None:
        args.optional_output.write_text(
            json.dumps({"enum": ["none", *options["enum"]]}) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(options))
    return 0


def validate_selection(args: argparse.Namespace) -> int:
    available = parse_checkpoint_options(args.checkpoint_options)
    choices = [name.strip() for name in args.selected_checkpoint]
    # Argo 4.1.1 may return the options JSON for untouched optional fields.
    optional_options = json.dumps({"enum": ["none", *available]})
    for index, choice in enumerate(choices[1:MAX_CHECKPOINT_SELECTIONS], start=1):
        if choice == optional_options:
            choices[index] = "none"
    if choices[0] == "none":
        raise ValueError("select at least one checkpoint")
    selected = [name for name in choices if name != "none"]
    if len(selected) > MAX_CHECKPOINT_SELECTIONS or len(selected) != len(set(selected)):
        raise ValueError(
            f"select one to {MAX_CHECKPOINT_SELECTIONS} distinct checkpoints"
        )

    # Recheck after the pause and restore only the selected archived checkpoints.
    trainer_output = resolve_trainer_output(args.runs_root, args.run_id)
    for name in selected:
        if name not in available:
            raise ValueError(f"unknown checkpoint selection: {name}")
    archives = (
        archived_checkpoints(trainer_output.parent)
        if any(not checkpoint_is_complete(trainer_output / name) for name in selected)
        else {}
    )
    for name in selected:
        resolve_checkpoint(trainer_output, name, archives=archives)

    args.output.write_text(json.dumps(selected) + "\n", encoding="utf-8")
    print(json.dumps({"selected_checkpoints": selected}))
    return 0


def restore(args: argparse.Namespace) -> int:
    trainer_output = resolve_trainer_output(args.runs_root, args.run_id)
    try:
        resolve_checkpoint(trainer_output, args.checkpoint)
    except UnarchivedIncompleteCheckpoint:
        # Existing model-only export inputs have no archive and need no
        # optimizer or resume state.
        if not (trainer_output / args.checkpoint / "config.json").is_file():
            raise
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=Path("/runs"))
    parser.add_argument("--run-id", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--output", type=Path, required=True)
    list_parser.add_argument("--optional-output", type=Path)
    list_parser.set_defaults(handler=write_options)

    validate_parser = subparsers.add_parser("validate-selection")
    validate_parser.add_argument("--checkpoint-options", required=True)
    validate_parser.add_argument("--selected-checkpoint", required=True, nargs="+")
    validate_parser.add_argument("--output", type=Path, required=True)
    validate_parser.set_defaults(handler=validate_selection)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--checkpoint", required=True)
    restore_parser.set_defaults(handler=restore)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

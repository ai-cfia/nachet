"""Validate and launch the reviewed Nachet detector training command."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

from checkpoint_state import (
    CHECKPOINT_PATTERN,
    checkpoint_is_complete,
    list_complete_checkpoints,
)

if TYPE_CHECKING:
    from mlflow import MlflowClient


RUN_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
GPU_PROFILES = ("ai-lab-1", "ai-lab-2", "ai-lab-3")
REQUIRED_RUNTIME_ENV = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "MLFLOW_ARTIFACT_BUCKET",
    "MLFLOW_EXPERIMENT_NAME",
    "MLFLOW_PUBLIC_URL",
    "MLFLOW_S3_ENDPOINT_URL",
    "MLFLOW_TRACKING_URI",
)
TRAINER_SOURCE = {
    "repository": "https://github.com/ai-cfia/nachet-model-ccds.git",
    "commit": "601219b7c9fcfc68f2ec51293edbab8cf3e0bc3a",
    "path": "nachetmodel/HFTrainer_detector_2026061501_js.py",
    "source_sha256": (
        "a45b39a9929b40d8b95f920dc2fcba6231690cdc35f06f3354ef766c10378fa6"
    ),
    "adaptation": "copied with a provenance header; behavior is unchanged",
}


@dataclass(frozen=True)
class DatasetProfile:
    root: str
    config: str
    model: str
    allowed_run_profiles: tuple[str, ...]
    expected_class_count: int | None


@dataclass(frozen=True)
class DatasetSourceEvidence:
    json_path: str
    json_sha256: str
    images_dir: str
    reject_list: str | None
    reject_list_sha256: str | None
    matched_classes: tuple[str, ...]


@dataclass(frozen=True)
class DatasetEvidence:
    sources: tuple[DatasetSourceEvidence, ...]
    included_classes: tuple[str, ...]


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


# Profiles constrain workflow input to reviewed paths and parameter sets.
DATASET_PROFILES = {
    "detector-smoke-v1": DatasetProfile(
        root="detector-smoke-v1",
        config="notebooks/shell/training_config_smoke.yaml",
        model="models/rtdetr_v2_r50vd",
        allowed_run_profiles=("smoke",),
        expected_class_count=None,
    ),
    "101-species-v1": DatasetProfile(
        root="101-species-v1",
        config="notebooks/shell/training_config_101spp_all.yaml",
        model="models/rtdetr_v2_r50vd",
        allowed_run_profiles=("smoke", "full"),
        expected_class_count=101,
    ),
}
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, object]) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def contained_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    resolved_path = (resolved_root / relative_path).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"path leaves its approved root: {relative_path}")
    return resolved_path


def require_path(path: Path, kind: Literal["file", "directory"]) -> None:
    valid = path.is_file() if kind == "file" else path.is_dir()
    if not valid:
        raise FileNotFoundError(f"required {kind} does not exist: {path}")


def load_dataset_config(dataset_config: Path) -> dict[str, object]:
    config_text = dataset_config.read_text(encoding="utf-8")
    try:
        config = json.loads(config_text)
    except json.JSONDecodeError:
        import yaml

        config = yaml.safe_load(config_text)
    if not isinstance(config, dict):
        raise TypeError("dataset configuration must contain a YAML mapping")
    return config


def validate_included_classes(
    config: dict[str, object],
    expected_class_count: int | None,
) -> tuple[str, ...]:
    included_classes = config.get("include_classes")
    if not isinstance(included_classes, list) or not included_classes:
        raise ValueError(
            "dataset configuration must contain a non-empty include_classes list"
        )
    if any(not isinstance(name, str) or not name.strip() for name in included_classes):
        raise ValueError("include_classes entries must be non-empty strings")
    if any(name != name.strip() for name in included_classes):
        raise ValueError("include_classes entries must not have surrounding whitespace")
    normalized_classes = [name.casefold() for name in included_classes]
    if len(normalized_classes) != len(set(normalized_classes)):
        raise ValueError("include_classes entries must be unique ignoring case")
    if (
        expected_class_count is not None
        and len(included_classes) != expected_class_count
    ):
        raise ValueError(
            f"dataset profile requires {expected_class_count} included classes, "
            f"found {len(included_classes)}"
        )
    if config.get("single_category") is not True:
        raise ValueError(
            "detector dataset configuration must set single_category: true"
        )
    if config.get("single_category_name") != "seed":
        raise ValueError(
            "detector dataset configuration must set single_category_name: seed"
        )
    return tuple(included_classes)


def resolve_source_path(
    source: dict[object, object],
    index: int,
    field: str,
    kind: Literal["file", "directory"],
    profile_root: Path,
) -> tuple[str, Path]:
    value = source.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"dataset source {index} needs {field}")
    path = contained_path(profile_root, value)
    require_path(path, kind)
    return value, path


def load_coco_category_names(json_path: Path, index: int) -> tuple[str, ...]:
    with json_path.open(encoding="utf-8") as handle:
        coco = json.load(handle)
    categories = coco.get("categories") if isinstance(coco, dict) else None
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"dataset source {index} has no COCO categories")

    category_names = []
    for category in categories:
        name = category.get("name") if isinstance(category, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"dataset source {index} has an invalid COCO category name"
            )
        category_names.append(name)
    normalized_names = [name.casefold() for name in category_names]
    if len(normalized_names) != len(set(normalized_names)):
        raise ValueError(f"dataset source {index} has duplicate COCO category names")
    return tuple(category_names)


def inspect_dataset_source(
    source: object,
    index: int,
    profile_root: Path,
    included_classes_by_name: dict[str, str],
) -> tuple[DatasetSourceEvidence, set[str]]:
    if not isinstance(source, dict):
        raise TypeError(f"dataset source {index} must be a mapping")

    json_path_text, json_path = resolve_source_path(
        source,
        index,
        "json_path",
        "file",
        profile_root,
    )
    images_dir_text, _ = resolve_source_path(
        source,
        index,
        "images_dir",
        "directory",
        profile_root,
    )

    reject_list = source.get("reject_list")
    reject_list_path = None
    if reject_list is not None:
        if not isinstance(reject_list, str) or not reject_list.strip():
            raise ValueError(f"dataset source {index} reject_list must be a path")
        reject_list_path = contained_path(profile_root, reject_list)
        require_path(reject_list_path, "file")

    category_names = load_coco_category_names(json_path, index)
    normalized_source_classes = [name.casefold() for name in category_names]
    matched_classes = tuple(
        included_classes_by_name[name]
        for name in normalized_source_classes
        if name in included_classes_by_name
    )
    evidence = DatasetSourceEvidence(
        json_path=json_path_text,
        json_sha256=sha256(json_path),
        images_dir=images_dir_text,
        reject_list=reject_list,
        reject_list_sha256=(
            sha256(reject_list_path) if reject_list_path is not None else None
        ),
        matched_classes=matched_classes,
    )
    return evidence, set(normalized_source_classes)


def validate_dataset_config(
    dataset_config: Path,
    profile_root: Path,
    expected_class_count: int | None,
) -> DatasetEvidence:
    config = load_dataset_config(dataset_config)
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("dataset configuration must contain at least one source")

    included_classes = validate_included_classes(config, expected_class_count)

    source_evidence = []
    available_classes: set[str] = set()
    included_classes_by_name = {name.casefold(): name for name in included_classes}
    for index, source in enumerate(sources):
        evidence, source_classes = inspect_dataset_source(
            source,
            index,
            profile_root,
            included_classes_by_name,
        )
        source_evidence.append(evidence)
        available_classes.update(source_classes)

    missing_classes = [
        name for name in included_classes if name.casefold() not in available_classes
    ]
    if missing_classes:
        raise ValueError(
            "include_classes entries are absent from the COCO category tables: "
            + ", ".join(missing_classes)
        )

    return DatasetEvidence(
        sources=tuple(source_evidence),
        included_classes=tuple(included_classes),
    )


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
    if not RUN_ID_PATTERN.fullmatch(resume_run_id):
        raise ValueError("resume-run-id must be a lowercase Kubernetes-style name")

    source_run = contained_path(runs_root, resume_run_id)
    require_path(source_run, "directory")
    trainer_output = contained_path(source_run, "trainer-output")
    require_path(trainer_output, "directory")

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
        requested_checkpoint = trainer_output / resume_checkpoint
        if requested_checkpoint.is_symlink():
            raise ValueError("resume-checkpoint must not be a symbolic link")
        checkpoint_path = contained_path(trainer_output, resume_checkpoint)
        require_path(checkpoint_path, "directory")

    if not checkpoint_is_complete(checkpoint_path):
        raise ValueError(f"checkpoint is incomplete: {checkpoint_path.name}")

    mlflow_run_id_path = contained_path(source_run, "mlflow-run-id")
    require_path(mlflow_run_id_path, "file")
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

        # Forward termination because this wrapper is PID 1 in the container.
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


def validate_runtime(gpu_profile: str) -> None:
    missing = [name for name in REQUIRED_RUNTIME_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "missing required training environment keys: " + ", ".join(missing)
        )

    scheduled_node = os.environ.get("KUBERNETES_NODE_NAME")
    if not scheduled_node:
        raise RuntimeError("KUBERNETES_NODE_NAME is not set")
    if scheduled_node != gpu_profile:
        raise RuntimeError(
            f"requested GPU profile {gpu_profile}, but Kubernetes scheduled "
            f"the pod on {scheduled_node}"
        )

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the training pod")
    if torch.cuda.device_count() != 1:
        visible_devices = torch.cuda.device_count()
        raise RuntimeError(f"expected one visible GPU, found {visible_devices}")


def open_mlflow_run(
    run_name: str,
    receipt_path: Path,
    dataset_config: Path,
    dataset_evidence: DatasetEvidence,
    profile_root: Path,
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
        client.log_artifact(
            run_id,
            str(receipt_path),
            artifact_path=f"requests/{run_name}",
        )
        client.log_artifact(
            run_id,
            str(dataset_config),
            artifact_path=f"requests/{run_name}",
        )
        for index, source in enumerate(dataset_evidence.sources, start=1):
            if source.reject_list is None:
                continue
            client.log_artifact(
                run_id,
                str(contained_path(profile_root, source.reject_list)),
                artifact_path=(f"requests/{run_name}/reject-lists/source-{index}"),
            )
    except Exception:
        # Do not replace the artifact error with a status-update failure.
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


def build_receipt(
    args: argparse.Namespace,
    run_profile: RunProfile,
    dataset_evidence: DatasetEvidence,
    dataset_config: Path,
    resume_run_id: str | None,
    resume_checkpoint: Path | None,
    command: list[str],
) -> dict[str, object]:
    included_classes_json = json.dumps(
        dataset_evidence.included_classes,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "dataset_profile": args.dataset_profile,
        "run_profile": args.run_profile,
        "effective_training_parameters": asdict(run_profile),
        "gpu_profile": args.gpu_profile,
        "run_id": args.run_id,
        "resume_run_id": resume_run_id,
        "resume_checkpoint": (
            str(resume_checkpoint) if resume_checkpoint is not None else None
        ),
        "dataset_source_count": len(dataset_evidence.sources),
        "dataset_sources": [asdict(source) for source in dataset_evidence.sources],
        "included_class_count": len(dataset_evidence.included_classes),
        "included_classes_sha256": hashlib.sha256(included_classes_json).hexdigest(),
        "dataset_config_sha256": sha256(dataset_config),
        "trainer_sha256": sha256(args.trainer_path),
        "trainer_source": TRAINER_SOURCE,
        "command": command,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and launch a reviewed Nachet detector training profile."
    )
    parser.add_argument(
        "--dataset-profile",
        choices=sorted(DATASET_PROFILES),
        required=True,
        help="reviewed dataset snapshot mounted below --input-root",
    )
    parser.add_argument(
        "--run-profile",
        choices=sorted(RUN_PROFILES),
        required=True,
        help="reviewed training parameter set",
    )
    parser.add_argument(
        "--gpu-profile",
        choices=GPU_PROFILES,
        required=True,
        help="GPU node selected by the WorkflowTemplate",
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
        help="lowercase identifier used as the immutable output directory name",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("/inputs"),
        help="root of the read-only dataset profile mount",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("/runs"),
        help="root of the persistent training output mount",
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
        help="earlier workflow run whose checkpoint and MLflow run should resume",
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
        help="validate inputs and write the request without starting training",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        raise ValueError("run-id must be a lowercase Kubernetes-style name")

    dataset = DATASET_PROFILES[args.dataset_profile]
    if args.run_profile not in dataset.allowed_run_profiles:
        raise ValueError(
            f"run profile {args.run_profile!r} is not allowed with dataset profile "
            f"{args.dataset_profile!r}"
        )
    run_profile = effective_run_profile(RUN_PROFILES[args.run_profile], args)
    profile_root = contained_path(args.input_root, dataset.root)
    dataset_config = contained_path(profile_root, dataset.config)
    model_path = contained_path(profile_root, dataset.model)
    run_root = contained_path(args.runs_root, args.run_id)
    output_path = contained_path(run_root, "trainer-output")

    resume_run_id = (
        None if args.resume_run_id in (None, "", "none") else args.resume_run_id
    )
    resume_runs_root = args.resume_runs_root or args.runs_root
    resume_checkpoint, existing_mlflow_run_id = resolve_resume_checkpoint(
        resume_runs_root,
        resume_run_id,
        args.resume_checkpoint,
    )

    require_path(dataset_config, "file")
    require_path(model_path, "directory")
    require_path(args.trainer_path, "file")
    dataset_evidence = validate_dataset_config(
        dataset_config,
        profile_root,
        dataset.expected_class_count,
    )

    run_root.mkdir(parents=True, exist_ok=False)
    output_path.mkdir()
    command = build_command(
        args.trainer_path,
        dataset_config,
        model_path,
        output_path,
        run_profile,
        resume_checkpoint,
    )

    receipt = build_receipt(
        args,
        run_profile,
        dataset_evidence,
        dataset_config,
        resume_run_id,
        resume_checkpoint,
        command,
    )
    receipt_path = run_root / "request.json"
    # Record the request before training so failed runs remain reproducible.
    write_json(receipt_path, receipt)

    if args.dry_run:
        print(json.dumps(receipt, indent=2))
        return 0

    mlflow_client = None
    mlflow_run_id = None
    mlflow_run_url = None
    try:
        validate_runtime(args.gpu_profile)

        # MLFLOW_RUN_ID links the migrated trainer to this wrapper-created run.
        mlflow_client, mlflow_run_id = open_mlflow_run(
            args.run_id,
            receipt_path,
            dataset_config,
            dataset_evidence,
            profile_root,
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
        (run_root / "mlflow-experiment-id").write_text(
            f"{mlflow_experiment_id}\n",
            encoding="utf-8",
        )
        (run_root / "mlflow-run-url").write_text(
            f"{mlflow_run_url}\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["MLFLOW_RUN_ID"] = mlflow_run_id
        # Let Transformers log each saved checkpoint to this MLflow run.
        environment["HF_MLFLOW_LOG_ARTIFACTS"] = "TRUE"
        return_code = run_and_tee(
            command,
            profile_root,
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
        write_json(
            run_root / "result.json",
            {
                "status": "succeeded" if return_code == 0 else "failed",
                "exit_code": return_code,
                "mlflow_run_id": mlflow_run_id,
                "mlflow_run_url": mlflow_run_url,
            },
        )
        return return_code
    except Exception as error:
        if mlflow_client is not None and mlflow_run_id is not None:
            with contextlib.suppress(Exception):
                mlflow_client.set_terminated(mlflow_run_id, status="FAILED")
        write_json(
            run_root / "result.json",
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
                "mlflow_run_id": mlflow_run_id,
                "mlflow_run_url": mlflow_run_url,
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())

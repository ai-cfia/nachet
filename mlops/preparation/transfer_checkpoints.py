"""Copy and verify checkpoints before an approved source cleanup."""

import argparse
import hashlib
import json
import logging
import os
import shutil
import stat
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from cleanup_checkpoints import (
    cleanup_checkpoints,
    open_directory,
    open_run,
    scan_checkpoints,
    validate_run_name,
)

RECEIPT = ".checkpoint-transfer.json"
logger = logging.getLogger(__name__)


@contextmanager
def checkpoint_file(directory: int, name: str):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError(f"Unsafe checkpoint file: {name}")
    with os.fdopen(fd, "rb") as stream:
        yield stream


@contextmanager
def prepared_directory(run_fd: int, path: Path):
    directory = open_directory(run_fd, "prepared", path)
    try:
        yield directory
    finally:
        os.close(directory)


def checkpoint_digest(directory: int, name: str) -> str:
    with checkpoint_file(directory, name) as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checkpoint_manifest(directory: int, prepared: Path) -> dict[str, str]:
    manifest = {}

    def record(parent: int, name: str, path: Path) -> None:
        manifest[path.relative_to(prepared).as_posix()] = checkpoint_digest(
            parent, name
        )

    scan_checkpoints(directory, prepared, visit=record)
    return manifest


def read_receipt(directory: int, source: str) -> dict[str, str]:
    with checkpoint_file(directory, RECEIPT) as stream:
        receipt = json.load(stream)
    if receipt["source"] != source:
        raise ValueError(
            f"Existing checkpoint transfer is from {receipt['source']}, not {source}"
        )
    return receipt["checksums"]


def copy_checkpoints(workspace: Path, source: str, target: str) -> int:
    validate_run_name(source)
    validate_run_name(target)
    if source == target:
        raise ValueError("Checkpoint transfer requires different workflow names")

    source_path = workspace / source / "prepared"
    target_path = workspace / target / "prepared"
    with open_run(workspace, target, create=True) as target_fd:
        try:
            os.stat("prepared", dir_fd=target_fd, follow_symlinks=False)
        except FileNotFoundError:
            # The first attempt has no prepared directory until the verified copy is published.
            pass
        else:
            # A retry after successful publication must preserve any local progress.
            with prepared_directory(target_fd, target_path) as directory:
                return len(read_receipt(directory, source))

        with (
            open_run(workspace, source) as source_fd,
            prepared_directory(source_fd, source_path) as source_directory,
            TemporaryDirectory(
                prefix=".checkpoint-transfer-", dir=target_path.parent
            ) as stage,
        ):
            staged = Path(stage) / "prepared"
            staged.mkdir()

            def copy(parent: int, name: str, path: Path) -> None:
                destination = staged / path.relative_to(source_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with (
                    checkpoint_file(parent, name) as original,
                    destination.open("xb") as output,
                ):
                    shutil.copyfileobj(original, output)

            scan_checkpoints(source_directory, source_path, visit=copy)
            with (
                open_directory_fd(staged.parent) as stage_fd,
                prepared_directory(stage_fd, staged) as staged_directory,
            ):
                expected = checkpoint_manifest(source_directory, source_path)
                if checkpoint_manifest(staged_directory, staged) != expected:
                    raise ValueError(
                        f"Checkpoint copy verification failed for {source}"
                    )
                (staged / RECEIPT).write_text(
                    json.dumps({"source": source, "checksums": expected}),
                    encoding="utf-8",
                )
                os.rename(
                    "prepared", "prepared", src_dir_fd=stage_fd, dst_dir_fd=target_fd
                )
    logger.info(
        "Copied and verified %d checkpoint files from %s to %s",
        len(expected),
        source,
        target,
    )
    return len(expected)


@contextmanager
def open_directory_fd(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


def cleanup_source(workspace: Path, source: str, target: str) -> int:
    validate_run_name(source)
    if source == target:
        raise ValueError("Checkpoint transfer requires different workflow names")
    target_path = workspace / target / "prepared"
    with (
        open_run(workspace, target) as target_fd,
        prepared_directory(target_fd, target_path) as directory,
    ):
        expected = read_receipt(directory, source)
        if checkpoint_manifest(directory, target_path) != expected:
            raise ValueError(f"Verified checkpoint copy changed in {target}")

    source_path = workspace / source / "prepared"

    def verify(parent: int, name: str, path: Path) -> None:
        # A cleanup retry may encounter only the files left by the first attempt.
        if expected.get(path.relative_to(source_path).as_posix()) != checkpoint_digest(
            parent, name
        ):
            raise ValueError(f"Source checkpoint changed after copying: {path}")

    return cleanup_checkpoints(workspace, source, verify=verify)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["copy", "cleanup"])
    parser.add_argument("workspace", type=Path)
    parser.add_argument("source")
    parser.add_argument("target")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.action == "copy":
        copied = copy_checkpoints(args.workspace, args.source, args.target)
        print("true" if copied else "false")
    else:
        cleanup_source(args.workspace, args.source, args.target)


if __name__ == "__main__":
    main()

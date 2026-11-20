"""Delete only one workflow's preparation and pre-label checkpoints."""

import argparse
import logging
import os
import re
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from checkpoint_version import parse_version

logger = logging.getLogger(__name__)
HEX_ID = re.compile(r"[0-9a-f]{64}")
RUN_PART = re.compile(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?")
PREPARATION_FILES = {
    "preparation.sqlite3",
    "preparation.sqlite3-wal",
    "preparation.sqlite3-shm",
    "preparation.sqlite3-journal",
}
CHECKPOINT_ROOTS = {
    "preparation-checkpoints": "preparation",
    "prelabel-checkpoints": "prelabel",
}
FileVisitor = Callable[[int, str, Path], None]


def validate_run_name(run_name: str) -> None:
    parts = run_name.split(".")
    if (
        len(run_name) > 253
        or run_name == "models"
        or any(len(part) > 63 or not RUN_PART.fullmatch(part) for part in parts)
    ):
        raise ValueError(f"Invalid workflow name for checkpoints: {run_name!r}")


def open_directory(parent: int, name: str, display: Path) -> int:
    try:
        return os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
        )
    except (NotADirectoryError, FileNotFoundError) as error:
        raise ValueError(
            f"Missing or unsafe checkpoint directory: {display}"
        ) from error


def child_kind(kind: str, name: str, path: Path) -> str:
    if kind == "preparation":
        parse_version(name, context=f"checkpoint directory {path}")
        return "preparation-version"
    if kind == "prelabel":
        if name == "releases":
            return "prelabel-releases"
        if HEX_ID.fullmatch(name):
            return "prelabel-legacy"
    if kind == "prelabel-releases" and HEX_ID.fullmatch(name):
        return "prelabel-identity"
    if kind == "prelabel-identity":
        parse_version(name, context=f"checkpoint directory {path}")
        return "prelabel-version"
    raise ValueError(f"Unexpected checkpoint directory: {path}")


def valid_checkpoint_file(kind: str, name: str) -> bool:
    if kind == "preparation-version":
        return name in PREPARATION_FILES or bool(
            re.fullmatch(
                r"\.snapshot-[a-zA-Z0-9_-]+\.sqlite3(?:-journal|-wal|-shm)?", name
            )
        )
    if kind == "prelabel-legacy":
        return bool(re.fullmatch(r"(?:[0-9]{8,}\.json|tmp[a-z0-9_]{8})", name))
    if kind == "prelabel-version":
        return bool(
            re.fullmatch(r"(?:[0-9]{8,}\.json|\.checkpoint-[a-zA-Z0-9_-]+\.tmp)", name)
        )
    return False


def visit_checkpoints(
    directory: int,
    kind: str,
    display: Path,
    *,
    delete: bool,
    visit: FileVisitor | None = None,
) -> int:
    removed = 0
    with os.scandir(directory) as entries:
        for entry in entries:
            path = display / entry.name
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISDIR(mode):
                next_kind = child_kind(kind, entry.name, path)
                child = open_directory(directory, entry.name, path)
                try:
                    removed += visit_checkpoints(
                        child, next_kind, path, delete=delete, visit=visit
                    )
                finally:
                    os.close(child)
                if delete:
                    os.rmdir(entry.name, dir_fd=directory)
            elif stat.S_ISREG(mode) and valid_checkpoint_file(kind, entry.name):
                if visit is not None:
                    visit(directory, entry.name, path)
                if delete:
                    os.unlink(entry.name, dir_fd=directory)
                    removed += 1
            else:
                raise ValueError(f"Unexpected or unsafe checkpoint entry: {path}")
    return removed


@contextmanager
def open_run(workspace: Path, run_name: str, *, create: bool = False) -> Iterator[int]:
    validate_run_name(run_name)
    if not workspace.is_absolute():
        raise ValueError("Workspace path must be absolute")
    workspace_fd = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if create:
            try:
                os.mkdir(run_name, dir_fd=workspace_fd)
            except FileExistsError:
                # Retries may find an existing run directory. Validate it when opening it.
                pass
        run_fd = open_directory(workspace_fd, run_name, workspace / run_name)
        try:
            yield run_fd
        finally:
            os.close(run_fd)
    finally:
        os.close(workspace_fd)


def scan_checkpoints(
    prepared_fd: int,
    prepared: Path,
    *,
    delete: bool = False,
    visit: FileVisitor | None = None,
) -> int:
    removed = 0
    for name in sorted(PREPARATION_FILES):
        try:
            mode = os.stat(name, dir_fd=prepared_fd, follow_symlinks=False).st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"Unsafe checkpoint file: {prepared / name}")
        if visit is not None:
            visit(prepared_fd, name, prepared / name)
        if delete:
            os.unlink(name, dir_fd=prepared_fd)
            removed += 1
    for name, kind in CHECKPOINT_ROOTS.items():
        try:
            os.stat(name, dir_fd=prepared_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        root_fd = open_directory(prepared_fd, name, prepared / name)
        try:
            removed += visit_checkpoints(
                root_fd, kind, prepared / name, delete=delete, visit=visit
            )
        finally:
            os.close(root_fd)
        if delete:
            os.rmdir(name, dir_fd=prepared_fd)
    return removed


def cleanup_checkpoints(
    workspace: Path, run_name: str, *, verify: FileVisitor | None = None
) -> int:
    prepared = workspace / run_name / "prepared"
    with open_run(workspace, run_name) as run_fd:
        prepared_fd = open_directory(run_fd, "prepared", prepared)
        try:
            scan_checkpoints(prepared_fd, prepared, visit=verify)
            removed = scan_checkpoints(prepared_fd, prepared, delete=True)
        finally:
            os.close(prepared_fd)
    logger.info("Removed %d checkpoint files from workflow %s", removed, run_name)
    return removed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument(
        "run_name", help="Workflow whose checkpoint files may be removed"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cleanup_checkpoints(args.workspace, args.run_name)


if __name__ == "__main__":
    main()

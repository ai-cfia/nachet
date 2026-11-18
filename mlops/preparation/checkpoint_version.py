"""Read preparation's project version and compare checkpoint releases."""

import tomllib
from pathlib import Path

from semver import Version

PROJECT_FILE = Path(__file__).with_name("pyproject.toml")


def parse_version(value: object, *, context: str) -> Version:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be a semantic version string: {value!r}")
    try:
        return Version.parse(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid semantic version for {context}: {value!r}"
        ) from error


def project_version() -> Version:
    try:
        with PROJECT_FILE.open("rb") as stream:
            project = tomllib.load(stream)["project"]
        value = project["version"]
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as error:
        raise ValueError(
            f"Cannot read project version from {PROJECT_FILE}: {error}"
        ) from error
    return parse_version(value, context=f"project version in {PROJECT_FILE}")


def compatible_checkpoint(checkpoint: Version, current: Version) -> bool:
    if checkpoint > current or checkpoint.major != current.major:
        return False
    return current.major != 0 or checkpoint.minor == current.minor


def compatible_directories(root: Path, current: Version) -> list[tuple[Version, Path]]:
    if root.is_symlink():
        raise ValueError(f"Checkpoint directory cannot be a symlink: {root}")
    if not root.exists():
        return []
    candidates = []
    for path in root.iterdir():
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"Invalid checkpoint version directory: {path}")
        version = parse_version(path.name, context=f"checkpoint directory {path}")
        if compatible_checkpoint(version, current):
            candidates.append((version, path))
    return sorted(
        candidates,
        key=lambda item: (item[0], item[1].name == str(current), item[1].name),
        reverse=True,
    )

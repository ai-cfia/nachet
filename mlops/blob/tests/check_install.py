"""Smoke-check an editable or wheel install without allowing backend imports."""

import importlib
import importlib.abc
import pkgutil
import sys
from importlib.metadata import distribution
from pathlib import Path


class BlockBackendImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "app" or fullname.startswith("app."):
            raise AssertionError(f"Blob package attempted backend import: {fullname}")
        return None


def check_install() -> None:
    sys.meta_path.insert(0, BlockBackendImports())
    package = importlib.import_module("blob")
    assert distribution("nachet-blob").read_text("top_level.txt").splitlines() == [
        "blob"
    ]
    package_root = Path(package.__file__).resolve().parent
    count = 0
    for info in pkgutil.walk_packages(package.__path__, "blob."):
        if info.name == "blob.tests" or info.name.startswith("blob.tests."):
            continue
        module = importlib.import_module(info.name)
        assert Path(module.__file__).resolve().is_relative_to(package_root), info.name
        if hasattr(module, "_get_logger"):
            module._get_logger()
        count += 1
    assert not any(name == "app" or name.startswith("app.") for name in sys.modules)
    print(f"Imported {count} blob modules from {package_root}; no backend imports")


if __name__ == "__main__":
    check_install()

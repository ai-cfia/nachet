"""Prove installed dataset tools use the sibling blob copy outside the source cwd."""

import subprocess
import sys
from pathlib import Path


def test_installed_dataset_tools_use_sibling_blob(tmp_path):
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-I", str(Path(__file__).with_name("check_install.py"))],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(project.parent / "blob" / "__init__.py") in result.stdout
    assert str(project / "dataset_release" / "__init__.py") in result.stdout
    assert "no backend or legacy imports" in result.stdout

import pytest
from semver import Version

import checkpoint_version as module


@pytest.mark.parametrize(
    "checkpoint,current,compatible",
    [
        ("0.2.0", "0.2.1", True),
        ("0.2.1", "0.2.0", False),
        ("0.1.9", "0.2.0", False),
        ("0.0.1", "0.0.2", True),
        ("1.2.0", "1.3.0", True),
        ("1.3.0", "1.2.0", False),
        ("1.9.9", "2.0.0", False),
        ("1.0.0-rc.1", "1.0.0", True),
        ("1.0.0", "1.0.0-rc.1", False),
        ("1.0.0+old", "1.0.0+new", True),
    ],
)
def test_compatible_checkpoint_versions(checkpoint, current, compatible):
    assert (
        module.compatible_checkpoint(Version.parse(checkpoint), Version.parse(current))
        is compatible
    )


def test_project_version_is_read_from_toml_and_invalid_versions_fail(
    tmp_path, monkeypatch
):
    project = tmp_path / "pyproject.toml"
    monkeypatch.setattr(module, "PROJECT_FILE", project)
    project.write_text('[project]\nversion = "0.2.3"\n')
    assert str(module.project_version()) == "0.2.3"
    project.write_text('[project]\nversion = "0.2.4-rc.1+build.2"\n')
    assert str(module.project_version()) == "0.2.4-rc.1+build.2"
    project.write_text('[project]\nversion = "1.2"\n')
    with pytest.raises(ValueError, match="Invalid semantic version"):
        module.project_version()
    project.unlink()
    with pytest.raises(ValueError, match="Cannot read project version"):
        module.project_version()


def test_compatible_directories_prefer_latest_without_using_newer(tmp_path):
    for version in ("0.1.9", "0.2.0", "0.2.1", "0.2.3", "0.3.0"):
        (tmp_path / version).mkdir()
    directories = module.compatible_directories(tmp_path, Version.parse("0.2.2"))
    assert [str(version) for version, _ in directories] == ["0.2.1", "0.2.0"]

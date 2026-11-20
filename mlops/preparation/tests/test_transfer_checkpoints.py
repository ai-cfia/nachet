import pytest

import transfer_checkpoints
from transfer_checkpoints import cleanup_source, copy_checkpoints

PREDICTIONS = f"prelabel-checkpoints/releases/{'a' * 64}/0.3.0"
DATABASE = "preparation-checkpoints/0.3.0/preparation.sqlite3"


def write_checkpoint(workspace, run, path, content=b"checkpoint"):
    checkpoint = workspace / run / "prepared" / path
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(content)
    return checkpoint


def test_verified_handoff_preserves_outputs_and_resumes_from_latest_run(tmp_path):
    source = write_checkpoint(tmp_path, "first-run", DATABASE)
    write_checkpoint(
        tmp_path, "first-run", DATABASE + "-wal", b"uncommitted or unmerged"
    )
    index = write_checkpoint(tmp_path, "first-run", "index.coco.json", b"index")
    assert copy_checkpoints(tmp_path, "first-run", "second-run") == 2
    assert source.exists()
    assert not (tmp_path / "second-run/prepared/index.coco.json").exists()
    assert cleanup_source(tmp_path, "first-run", "second-run") == 2
    assert cleanup_source(tmp_path, "first-run", "second-run") == 0
    assert not source.exists()
    assert index.read_bytes() == b"index"

    prediction = write_checkpoint(
        tmp_path, "second-run", f"{PREDICTIONS}/00000001.json"
    )
    assert copy_checkpoints(tmp_path, "first-run", "second-run") == 2
    assert prediction.exists()
    assert copy_checkpoints(tmp_path, "second-run", "third-run") == 3
    assert cleanup_source(tmp_path, "second-run", "third-run") == 3
    assert (tmp_path / "third-run/prepared" / PREDICTIONS / prediction.name).is_file()


def test_checksum_mismatch_preserves_source_without_publishing_copy(
    tmp_path, monkeypatch
):
    source = write_checkpoint(tmp_path, "first-run", DATABASE)
    monkeypatch.setattr(
        transfer_checkpoints.shutil,
        "copyfileobj",
        lambda source, target: target.write(b"corrupt"),
    )
    with pytest.raises(ValueError, match="verification failed"):
        copy_checkpoints(tmp_path, "first-run", "second-run")
    assert source.read_bytes() == b"checkpoint"
    assert not (tmp_path / "second-run/prepared").exists()
    assert not list((tmp_path / "second-run").iterdir())


@pytest.mark.parametrize("changed_run", ["first-run", "second-run"])
def test_cleanup_refuses_modified_source_or_destination(tmp_path, changed_run):
    source = write_checkpoint(tmp_path, "first-run", DATABASE)
    prediction = write_checkpoint(tmp_path, "first-run", f"{PREDICTIONS}/00000001.json")
    assert copy_checkpoints(tmp_path, "first-run", "second-run") == 2
    write_checkpoint(tmp_path, changed_run, DATABASE, b"changed")
    with pytest.raises(ValueError, match="changed"):
        cleanup_source(tmp_path, "first-run", "second-run")
    assert source.exists()
    assert prediction.exists()


def test_copy_refuses_overwriting_existing_progress_without_receipt(tmp_path):
    source = write_checkpoint(tmp_path, "first-run", DATABASE)
    local = write_checkpoint(tmp_path, "second-run", DATABASE, b"new progress")
    with pytest.raises(FileNotFoundError, match=transfer_checkpoints.RECEIPT):
        copy_checkpoints(tmp_path, "first-run", "second-run")
    assert source.read_bytes() == b"checkpoint"
    assert local.read_bytes() == b"new progress"

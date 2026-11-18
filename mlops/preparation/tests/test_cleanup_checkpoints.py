import pytest

from cleanup_checkpoints import cleanup_checkpoints


def write(path, data=b"checkpoint"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_cleanup_removes_only_selected_run_checkpoints_and_is_idempotent(tmp_path):
    prepared = tmp_path / "current-run" / "prepared"
    legacy_image = prepared / "prelabel-checkpoints" / ("a" * 64) / "00000000.json"
    versioned_image = (
        prepared
        / "prelabel-checkpoints"
        / "releases"
        / ("b" * 64)
        / "0.3.0"
        / "00000001.json"
    )
    targets = [
        prepared / "preparation.sqlite3",
        prepared / "preparation.sqlite3-wal",
        prepared / "preparation-checkpoints/0.3.0/preparation.sqlite3",
        prepared / "preparation-checkpoints/0.3.0/.snapshot-abcd.sqlite3",
        legacy_image,
        legacy_image.with_name("tmpabcdefgh"),
        versioned_image,
        versioned_image.with_name(".checkpoint-abcd.tmp"),
    ]
    for path in targets:
        write(path)
    preserved = [
        prepared / "index.coco.json",
        prepared / "draft.coco.json",
        prepared / "checksum-audit.json",
        tmp_path / "previous-run/prepared/preparation.sqlite3",
        tmp_path / "models/sam3/weights",
    ]
    for path in preserved:
        write(path, b"preserve")

    assert cleanup_checkpoints(tmp_path, "current-run") == len(targets)
    assert all(not path.exists() for path in targets)
    assert not (prepared / "preparation-checkpoints").exists()
    assert not (prepared / "prelabel-checkpoints").exists()
    assert all(path.read_bytes() == b"preserve" for path in preserved)
    assert cleanup_checkpoints(tmp_path, "current-run") == 0


@pytest.mark.parametrize(
    "run_name", ["../other", "/other", "a..b", "models", "UPPER", "-invalid", ""]
)
def test_cleanup_rejects_invalid_or_reserved_run_names(tmp_path, run_name):
    with pytest.raises(ValueError, match="Invalid workflow name"):
        cleanup_checkpoints(tmp_path, run_name)


@pytest.mark.parametrize("location", ["run", "prepared", "root", "nested", "legacy"])
def test_cleanup_rejects_symlinks_without_deleting_other_checkpoints(
    tmp_path, location
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data").write_text("preserve")
    run = tmp_path / "run"
    prepared = run / "prepared"
    if location == "run":
        run.symlink_to(outside, target_is_directory=True)
    elif location == "prepared":
        run.mkdir()
        prepared.symlink_to(outside, target_is_directory=True)
    else:
        write(prepared / "preparation.sqlite3", b"legacy")
        if location == "root":
            (prepared / "prelabel-checkpoints").symlink_to(
                outside, target_is_directory=True
            )
        elif location == "nested":
            root = prepared / "prelabel-checkpoints"
            root.mkdir()
            (root / ("a" * 64)).symlink_to(outside, target_is_directory=True)
        else:
            (prepared / "preparation.sqlite3-wal").symlink_to(outside / "data")
    with pytest.raises((ValueError, OSError)):
        cleanup_checkpoints(tmp_path, "run")
    assert (outside / "data").read_text() == "preserve"
    if location not in {"run", "prepared"}:
        assert (prepared / "preparation.sqlite3").read_bytes() == b"legacy"


def test_cleanup_refuses_unrecognized_checkpoint_data_before_deleting(tmp_path):
    prepared = tmp_path / "run" / "prepared"
    legacy = prepared / "preparation.sqlite3"
    unexpected = prepared / "prelabel-checkpoints" / ("a" * 64) / "review-notes.txt"
    write(legacy)
    write(unexpected, b"preserve")
    with pytest.raises(ValueError, match="Unexpected or unsafe checkpoint entry"):
        cleanup_checkpoints(tmp_path, "run")
    assert legacy.exists()
    assert unexpected.read_bytes() == b"preserve"

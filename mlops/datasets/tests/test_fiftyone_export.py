"""Labels-only export, unambiguous path joins, and release preparation."""

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from dataset_controller.models.dataset import CocoImage, ReleaseSpec, sha256

from dataset_release.fiftyone_export import (
    ImageMembership,
    export_collection,
    image_digest,
    main,
    remap_coco,
)


@pytest.fixture
def handoff():
    # Same basename in different folders must never be joined by basename.
    paths = ["/datasets/a/seed.png", "/datasets/b/seed.png"]
    coco = {
        "info": {"description": "Corrected labels"},
        "images": [
            {"id": 17, "file_name": paths[0], "width": 20, "height": 10},
            {"id": 29, "file_name": paths[1], "width": 20, "height": 10},
        ],
        "categories": [{"id": 6, "name": "Avena"}],
        "annotations": [
            {
                "id": 81,
                "image_id": 17,
                "category_id": 6,
                "bbox": [1.25, 2.5, 4.5, 3.0],
                "reviewer": "reviewer-1",
            }
        ],
    }
    members = [
        ImageMembership(
            file_name=path,
            sha256=str(index) * 64,
            split=split,
            sources=[{"original_path": path, "specimen_group": f"specimen-{index}"}],
        )
        for index, (path, split) in enumerate(zip(paths, ("train", "test")), 1)
    ]
    return coco, members


def test_remap_preserves_reviewed_labels_and_negative_images(handoff):
    coco, members = handoff
    original = deepcopy(coco)
    result = remap_coco(coco, reversed(members))
    assert coco == original
    assert [image.id for image in result.images] == [17, 29]
    assert [image.file_name for image in result.images] == [
        f"png/detection/{member.sha256}.png" for member in members
    ]
    assert result.images[0].sha256 == members[0].sha256
    assert result.images[1].split == "test"
    assert result.images[0].sources == members[0].sources
    assert result.annotations[0].bbox == coco["annotations"][0]["bbox"]
    assert result.annotations[0].reviewer == "reviewer-1"
    assert result.info == coco["info"]
    assert result.categories[0].id == 6


@pytest.mark.parametrize("failure", ["missing", "extra", "duplicate", "duplicate_coco"])
def test_remap_rejects_incomplete_or_ambiguous_membership(handoff, failure):
    coco, members = handoff
    if failure == "missing":
        members.pop()
    elif failure == "extra":
        members.append(members[0].model_copy(update={"file_name": "/extra.png"}))
    elif failure == "duplicate":
        members.append(members[0])
    else:
        coco["images"].append({**coco["images"][0], "id": 50})
    with pytest.raises(ValueError, match="[Mm]embership|[Dd]uplicate"):
        remap_coco(coco, members)


@pytest.mark.parametrize("field", ["sha256", "split", "sources", "file_name"])
def test_remap_rejects_conflicting_metadata(handoff, field):
    coco, members = handoff
    image = coco["images"][0]
    image[field] = {
        "sha256": "f" * 64,
        "split": "validation",
        "sources": [{"original_path": "some-other-path"}],
        "file_name": f"/datasets/{'f' * 64}.png",
    }[field]
    if field == "file_name":
        members[0] = members[0].model_copy(update={"file_name": image[field]})
    with pytest.raises(ValueError, match="differs|differ"):
        remap_coco(coco, members)


def test_remap_preserves_existing_sources_and_normalizes_windows_separators(handoff):
    coco, members = handoff
    coco["images"][0]["sources"] = [{"original_path": "original.tiff"}]
    members[0] = members[0].model_copy(update={"sources": []})
    for image in coco["images"]:
        image["file_name"] = image["file_name"].replace("/", "\\")
    result = remap_coco(coco, members)
    assert result.images[0].sources[0].original_path == "original.tiff"


def test_matching_sources_do_not_conflict_when_optional_fields_are_omitted(handoff):
    coco, members = handoff
    coco["images"][0]["sources"] = [
        {"original_path": members[0].file_name, "specimen_group": "specimen-1"}
    ]
    assert remap_coco(coco, members).images[0].sources == members[0].sources


@pytest.mark.parametrize("digest", [None, "invalid", "f" * 64, 123])
def test_explicit_coco_hash_must_match_key(handoff, digest):
    coco, members = handoff
    data = remap_coco(coco, members).images[0].model_dump(mode="json")
    data["sha256"] = digest
    with pytest.raises(ValueError, match="SHA-256"):
        CocoImage.model_validate(data)


def test_legacy_images_keep_their_serialized_shape_without_optional_hash(handoff):
    coco, members = handoff
    data = remap_coco(coco, members).images[0].model_dump(mode="json")
    del data["sha256"]
    assert CocoImage.model_validate(data).model_dump(mode="json") == data


@pytest.mark.parametrize("split", [None, "val", ["train", "test"]])
def test_membership_requires_one_explicit_supported_split(handoff, split):
    data = handoff[1][0].model_dump(mode="json")
    data["split"] = split
    with pytest.raises(ValueError):
        ImageMembership.model_validate(data)


def test_image_hash_uses_exact_bytes_or_stored_identity_without_copying(tmp_path):
    source = tmp_path / "seed.png"
    source.write_bytes(b"exact-file-bytes")
    digest = sha256(source.read_bytes())
    assert image_digest(str(source), None) == digest
    assert image_digest("/not-mounted/seed.png", digest) == digest
    assert image_digest(f"/not-mounted/{digest}.png", None) == digest
    with pytest.raises(ValueError, match="differs"):
        image_digest(f"/not-mounted/{digest}.png", "f" * 64)
    assert list(tmp_path.iterdir()) == [source]


@pytest.fixture
def fiftyone_stub(monkeypatch, handoff):
    coco, members = handoff
    detection_type = object()
    fo = SimpleNamespace(
        Detections=object(), types=SimpleNamespace(COCODetectionDataset=detection_type)
    )
    monkeypatch.setitem(sys.modules, "fiftyone", fo)
    samples = []
    for index, member in enumerate(members):
        fields = member.model_dump(mode="json")
        fields["corrected_detections"] = SimpleNamespace(
            detections=[object()] if index == 0 else []
        )
        if index == 1:
            del fields["sources"]
        samples.append(
            SimpleNamespace(
                filepath=member.file_name, id=str(index), get_field=fields.get
            )
        )
    collection = Mock()
    collection.iter_samples.return_value = iter(samples)

    def export(**kwargs):
        Path(kwargs["labels_path"]).write_text(json.dumps(coco), encoding="utf-8")

    collection.export.side_effect = export
    fo.load_dataset = Mock(return_value=collection)
    return fo, collection


def test_fiftyone_export_only_requests_labels_with_absolute_paths(
    fiftyone_stub, handoff
):
    fo, collection = fiftyone_stub
    reviewed = export_collection(collection, "corrected_detections")
    kwargs = collection.export.call_args.kwargs
    assert kwargs["export_media"] is False
    assert kwargs["abs_paths"] is True
    assert kwargs["extra_attrs"] is True
    assert kwargs["label_field"] == "corrected_detections"
    assert kwargs["dataset_type"] is fo.types.COCODetectionDataset
    assert "export_dir" not in kwargs and "data_path" not in kwargs
    assert not Path(kwargs["labels_path"]).exists()  # temporary JSON is cleaned up
    assert reviewed.images[1].sources[0].fiftyone_sample_id == "1"
    assert reviewed.annotations[0].bbox == handoff[0]["annotations"][0]["bbox"]


def test_fiftyone_rejects_non_detection_fields(fiftyone_stub):
    _, collection = fiftyone_stub
    collection.get_field.return_value = None
    with pytest.raises(ValueError, match="Detections"):
        export_collection(collection, "wrong_field")
    collection.export.assert_not_called()


def test_fiftyone_rejects_unreviewed_null_labels(fiftyone_stub):
    _, collection = fiftyone_stub
    with pytest.raises(ValueError, match="Each sample needs reviewed detections"):
        export_collection(collection, "missing_labels")
    collection.export.assert_not_called()


def test_fiftyone_rejects_silently_dropped_annotations(fiftyone_stub, handoff):
    _, collection = fiftyone_stub
    handoff[0]["annotations"] = []
    with pytest.raises(ValueError, match="retain every reviewed detection"):
        export_collection(collection, "corrected_detections")


@pytest.fixture
def prepare_args(tmp_path, handoff):
    coco, members = handoff
    inputs = {
        "coco.json": coco,
        "membership.json": [member.model_dump(mode="json") for member in members],
        "metadata.json": {
            "name": "reviewed-seeds",
            "version": "v1",
            "author": "reviewer",
            "conversion": {"code_revision": "png-v1", "settings": {}},
        },
    }
    for name, value in inputs.items():
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    return [
        "--coco",
        str(tmp_path / "coco.json"),
        "--membership",
        str(tmp_path / "membership.json"),
        "--release-metadata",
        str(tmp_path / "metadata.json"),
        "--output-dir",
        str(tmp_path / "release"),
    ]


def test_offline_command_writes_publishable_spec_and_coco_without_fiftyone(
    prepare_args, tmp_path, monkeypatch
):
    monkeypatch.setitem(sys.modules, "fiftyone", None)
    assert main(prepare_args) == 0
    output = tmp_path / "release"
    spec = ReleaseSpec.model_validate_json(
        (output / "dataset-release.json").read_bytes()
    )
    assert spec.generate_crops is False
    assert spec.coco.model_dump(mode="json") == json.loads(
        (output / "coco.json").read_text(encoding="utf-8")
    )
    assert sorted(path.name for path in output.iterdir()) == [
        "coco.json",
        "dataset-release.json",
    ]
    with pytest.raises(SystemExit, match="already exists"):
        main(prepare_args)


def test_dataset_command_exports_saved_reviewed_view(
    prepare_args, tmp_path, fiftyone_stub
):
    fo, view = fiftyone_stub
    dataset = Mock()
    dataset.load_saved_view.return_value = view
    fo.load_dataset.return_value = dataset
    args = [
        "--dataset",
        "seeds",
        "--view",
        "reviewed",
        "--label-field",
        "corrected_detections",
        *prepare_args[4:],
    ]
    assert main(args) == 0
    fo.load_dataset.assert_called_once_with("seeds")
    dataset.load_saved_view.assert_called_once_with("reviewed")
    spec = ReleaseSpec.model_validate_json(
        (tmp_path / "release" / "dataset-release.json").read_bytes()
    )
    assert spec.generate_crops is False


def test_failed_preparation_leaves_no_output_folder(prepare_args, tmp_path):
    (tmp_path / "membership.json").write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit, match="Missing membership"):
        main(prepare_args)
    assert not (tmp_path / "release").exists()


def test_preparation_refuses_crop_generation(prepare_args, tmp_path):
    metadata_path = tmp_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["generate_crops"] = True
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(SystemExit, match="generate_crops=false"):
        main(prepare_args)
    assert not (tmp_path / "release").exists()

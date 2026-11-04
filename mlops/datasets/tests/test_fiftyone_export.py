"""Labels-only export, unambiguous path joins, and release preparation."""

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dataset_release.contract import (
    CocoImage,
    ConversionRecipe,
    ReleaseDefinition,
    ReleaseSpec,
    sha256,
)
from dataset_release.fiftyone_export import (
    ImageMembership,
    export_collection,
    image_digest,
    parse_args,
    prepare,
    remap_coco,
)
from dataset_release.registry import Base
from dataset_release.release import DatasetController, ReleaseConflict


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


@pytest.mark.parametrize(
    "exported_paths",
    [
        ["seed.png", "seed-2.png"],
        ["a/seed.png", "b/seed.png"],
        ["/export/data/seed.png", "/export/data/seed-2.png"],
    ],
)
def test_remap_requires_explicit_membership_for_rewritten_export_paths(
    handoff, exported_paths
):
    coco, members = handoff
    for image, path in zip(coco["images"], exported_paths):
        image["file_name"] = path

    # Original sample paths cannot identify flattened/renamed export paths.
    with pytest.raises(ValueError, match="Absolute paths enabled"):
        remap_coco(coco, members)

    # An explicit mapping using the actual export keys is supported, including
    # relative paths; never infer membership from basename or export order.
    exported_members = [
        member.model_copy(update={"file_name": path})
        for member, path in zip(members, exported_paths)
    ]
    reviewed = remap_coco(coco, reversed(exported_members))
    assert [image.sha256 for image in reviewed.images] == [
        member.sha256 for member in members
    ]
    assert [image.split for image in reviewed.images] == ["train", "test"]


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
    reviewed, members = export_collection(collection, "corrected_detections")
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


@pytest_asyncio.fixture
async def draft(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'draft.sqlite'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    controller = DatasetController(None, async_sessionmaker(engine), "datasets")
    await controller.create_release(
        ReleaseDefinition(
            name="reviewed-seeds",
            version="v1",
            author="reviewer",
            conversion=ConversionRecipe(
                code_revision="png-v1", settings={"mode": "RGB"}
            ),
        )
    )
    try:
        yield controller
    finally:
        await engine.dispose()


def export_args(*source):
    return parse_args(
        [
            "--container",
            "datasets",
            "--name",
            "reviewed-seeds",
            "--version",
            "v1",
            *source,
        ]
    )


@pytest.mark.asyncio
async def test_offline_preparation_reads_database_and_generates_json_on_request(
    draft, handoff, tmp_path, monkeypatch
):
    monkeypatch.setitem(sys.modules, "fiftyone", None)
    coco, members = handoff
    for member in reversed(members):
        await draft.catalog.add_membership("reviewed-seeds", "v1", member)
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps(coco), encoding="utf-8")
    args = export_args("--coco", str(labels))
    spec = await prepare(args, draft)
    assert spec.author == "reviewer"
    assert spec.conversion.settings == {"mode": "RGB"}
    assert spec.coco == remap_coco(coco, members)
    assert not (tmp_path / "release").exists()
    generated = await draft.export_json("reviewed-seeds", "v1", "spec")
    assert ReleaseSpec.model_validate_json(generated) == spec
    exported_members = json.loads(
        await draft.export_json("reviewed-seeds", "v1", "membership")
    )
    assert [member["file_name"] for member in exported_members] == [
        member.file_name for member in members
    ]

    args.output_dir = tmp_path / "release"
    assert await prepare(args, draft) == spec
    assert (args.output_dir / "dataset-release.json").read_bytes() == generated
    with pytest.raises(ValueError, match="already exists"):
        await prepare(args, draft)


@pytest.mark.asyncio
async def test_dataset_command_saves_membership_from_saved_reviewed_view(
    draft, fiftyone_stub
):
    fo, view = fiftyone_stub
    dataset = Mock()
    dataset.load_saved_view.return_value = view
    fo.load_dataset.return_value = dataset
    spec = await prepare(
        export_args(
            "--dataset",
            "seeds",
            "--view",
            "reviewed",
            "--label-field",
            "corrected_detections",
        ),
        draft,
    )
    fo.load_dataset.assert_called_once_with("seeds")
    dataset.load_saved_view.assert_called_once_with("reviewed")
    members = await draft.catalog.memberships("reviewed-seeds", "v1")
    assert [item.file_name for item in members] == [
        "/datasets/a/seed.png",
        "/datasets/b/seed.png",
    ]
    assert members[1].sources[0].fiftyone_sample_id == "1"
    assert spec.coco == (await draft.catalog.spec("reviewed-seeds", "v1")).coco


@pytest.mark.asyncio
async def test_missing_database_membership_leaves_draft_unchanged(
    draft, handoff, tmp_path
):
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps(handoff[0]), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing membership"):
        await prepare(export_args("--coco", str(labels)), draft)
    assert await draft.catalog.memberships("reviewed-seeds", "v1") == []
    assert (
        await draft.get_release_registration("reviewed-seeds", "v1")
    ).status == "draft"


@pytest.mark.asyncio
async def test_draft_membership_rejects_duplicate_normalized_paths(draft, handoff):
    member = handoff[1][0]
    await draft.catalog.add_membership("reviewed-seeds", "v1", member)
    with pytest.raises(ReleaseConflict, match="Duplicate membership"):
        await draft.catalog.add_membership(
            "reviewed-seeds",
            "v1",
            member.model_copy(
                update={"file_name": member.file_name.replace("/", "\\")}
            ),
        )

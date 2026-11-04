"""Execute the WorkflowTemplate's commands with synthetic inference and storage."""

import hashlib
import importlib
from pathlib import Path

import pytest
import yaml
from PIL import Image

import s3_storage
from prelabel import Prediction


def test_workflow_commands_reach_fiftyone_without_losing_source_identity(
    tmp_path, fiftyone, review_name, s3_provider, monkeypatch
):
    original = tmp_path / "collection"
    for index, relative in enumerate(
        [
            "Training/Avena fatua/batch/tray/one.tiff",
            "Validation/Avena fatua/two.tiff",
            "Zea mays/three.png",
        ]
    ):
        path = original / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (12, 10), (index * 60, 20, 30)).save(path)
    monkeypatch.setattr(
        s3_storage,
        "create_blob_storage_client",
        lambda *args, **kwargs: s3_provider.storage,
    )
    # Keep the workflow offline: supply draft boxes instead of loading SAM3 weights.
    import prelabel

    monkeypatch.setattr(
        prelabel,
        "Sam3Predictor",
        lambda *args: lambda image: Prediction([[1.0, 1.0, 5.0, 5.0]], "synthetic"),
    )
    for path in original.rglob("*"):
        if path.is_file():
            key = "raw/collection/" + path.relative_to(original).as_posix()
            s3_provider.objects["datasets", key] = path.read_bytes()
    spec = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2]
            / "workflows/preparation-workflow-template.yaml"
        ).read_text()
    )["spec"]
    templates = {template["name"]: template for template in spec["templates"]}
    values = {
        "raw-prefix": "raw/collection",
        "code-revision": "test-revision",
        "dataset-name": review_name,
    }
    config = {
        "bucket": "datasets",
        "endpoint-url": "https://storage.example.test",
        "region": "test",
        "model-revision": "synthetic-weights",
        "server-media-root": "/fiftyone-s3",
    }

    def run_step(name):
        container = templates[name]["container"]
        environment = {
            entry["name"]: config[entry["valueFrom"]["configMapKeyRef"]["key"]]
            for entry in container.get("env", [])
        }
        args = []
        for value in container["args"]:
            for key, replacement in values.items():
                value = value.replace(
                    "{{workflow.parameters." + key + "}}", replacement
                )
            for key, replacement in environment.items():
                value = value.replace("$(" + key + ")", replacement)
            value = value.replace("{{workflow.name}}", "preparation-test-run")
            value = value.replace("/workspace", str(tmp_path / "workspace"))
            assert "{{" not in value
            assert "$(" not in value
            args.append(value)
        assert container["command"][0] == "python"
        module = importlib.import_module(Path(container["command"][1]).stem)
        module.main(args)

    for step in templates["prepare-for-review"]["steps"]:
        run_step(step[0]["template"])
    dataset = fiftyone.load_dataset(review_name)
    assert len(dataset) == 3
    assert set(dataset.values("split")) == {"train", "validation", None}
    for sample in dataset:
        source = sample.sources[0]
        raw = (original / source["original_path"]).read_bytes()
        assert source["raw_sha256"] == hashlib.sha256(raw).hexdigest()
        assert source["raw_key"] == "raw/collection/" + source["original_path"]
        assert s3_provider.objects["datasets", source["raw_key"]] == raw
        png = s3_provider.objects["datasets", sample.object_key]
        assert sample.image_sha256 == hashlib.sha256(png).hexdigest()
        assert sample.filepath == "/fiftyone-s3/" + sample.object_key
        assert len(sample.draft_boxes.detections) == 1
    before = dict(s3_provider.objects)
    for name in ("prepare-images", "prelabel"):
        run_step(name)
    assert s3_provider.objects == before
    workspace_files = {
        p.name for p in (tmp_path / "workspace").rglob("*") if p.is_file()
    }
    assert workspace_files == {"index.coco.json", "draft.coco.json"}
    with pytest.raises(ValueError, match="already exists"):
        run_step("register-for-review")
    assert len(fiftyone.load_dataset(review_name)) == 3

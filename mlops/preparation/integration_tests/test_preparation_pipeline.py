"""Execute the WorkflowTemplate's commands with synthetic inference and storage."""

import hashlib
import importlib
import io
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

import s3_storage
from prelabel import Prediction


@pytest.mark.parametrize("policy", [None, "warn"], ids=["default-strict", "warn"])
def test_workflow_preparation_duplicate_policy(
    tmp_path, s3_provider, monkeypatch, policy
):
    spec = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2]
            / "workflows/preparation-workflow-template.yaml"
        ).read_text()
    )["spec"]
    values = {
        parameter["name"]: parameter["value"]
        for parameter in spec["arguments"]["parameters"]
        if "value" in parameter
    }
    values.update({"raw-prefix": "raw/collection", "code-revision": "test"})
    if policy is not None:
        values["duplicate-conflicts"] = policy
    container = next(
        template["container"]
        for template in spec["templates"]
        if template["name"] == "prepare-images"
    )
    replacements = {
        "/workspace": str(tmp_path),
        "{{workflow.name}}": "bypass-test",
        "$(PREPARATION_BUCKET)": "datasets",
        "$(PREPARATION_S3_ENDPOINT_URL)": "http://cold-storage.example.test",
        "$(PREPARATION_REGION)": "test",
    }
    replacements.update(
        {"{{workflow.parameters." + key + "}}": value for key, value in values.items()}
    )
    args = list(container["args"])
    for source, replacement in replacements.items():
        args = [argument.replace(source, replacement) for argument in args]
    assert all("{{" not in argument and "$(" not in argument for argument in args)

    content = io.BytesIO()
    Image.new("RGB", (3, 2), "gray").save(content, format="TIFF")
    keys = [
        "raw/collection/Amaranthus albus/ColorChecker.tiff",
        "raw/collection/Amaranthus palmeri/ColorChecker.tiff",
    ]
    for key in keys:
        s3_provider.objects["datasets", key] = content.getvalue()
    module = importlib.import_module(Path(container["command"][1]).stem)
    monkeypatch.setattr(
        module, "create_storage", lambda *args, **kwargs: s3_provider.storage
    )
    if policy is None:
        with pytest.raises(ValueError, match="conflicting species or splits"):
            module.main(args)
        assert not (Path(args[0]) / "index.coco.json").exists()
    else:
        module.main(args)
        result = json.loads((Path(args[0]) / "index.coco.json").read_text())
        assert len(result["images"]) == 1
        assert [source["raw_key"] for source in result["images"][0]["sources"]] == keys
        s3_provider.client.put_object.assert_called_once()


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
    cold_endpoint = "http://cold-storage.example.test"

    def s3_client(service, *, endpoint_url, region_name, **kwargs):
        assert service == "s3"
        assert endpoint_url == cold_endpoint
        assert region_name == "test"
        return s3_provider.client

    monkeypatch.setattr(s3_storage.boto3, "client", s3_client)
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
        "model-revision": "synthetic-weights",
        "duplicate-conflicts": "error",
    }
    config_maps = {
        "nachet-preparation-config": {
            "bucket": "datasets",
            "endpoint-url": cold_endpoint,
            "region": "test",
            "server-media-root": "/fiftyone-preparation",
        },
    }
    secrets = {
        "nachet-preparation-cold-s3": {},
        # The fiftyone fixture supplies the isolated database connection.
        "nachet-preparation-fiftyone": {},
    }

    def run_step(name):
        container = templates[name]["container"]
        environment = {}
        for entry in container.get("env", []):
            ref = entry["valueFrom"]["configMapKeyRef"]
            environment[entry["name"]] = config_maps[ref["name"]][ref["key"]]
        for source in container.get("envFrom", []):
            environment.update(secrets[source["secretRef"]["name"]])
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
    assert dataset.info["prelabel"]["model_revision"] == "synthetic-weights"
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
        assert sample.filepath == "/fiftyone-preparation/" + sample.object_key
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

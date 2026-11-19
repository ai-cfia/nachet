"""Execute the WorkflowTemplate's commands with synthetic inference and storage."""

import hashlib
import importlib
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml
from blob.exceptions import BlobStorageError
from PIL import Image
from semver import Version

import s3_storage
from cleanup_checkpoints import cleanup_checkpoints
from prelabel import Prediction


def preparation_command(
    tmp_path,
    workflow_name,
    *,
    step="prepare-images",
    entrypoint="prepare-for-review",
    **parameters,
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
    values.update(parameters)
    templates = {template["name"]: template for template in spec["templates"]}
    template = templates[step]
    container = template["container"]
    input_parameters = template.get("inputs", {}).get("parameters", [])
    inputs = {
        parameter["name"]: parameter["default"]
        for parameter in input_parameters
        if "default" in parameter
    }
    if entrypoint == step:
        inputs.update(
            {
                parameter["name"]: values[parameter["name"]]
                for parameter in input_parameters
                if parameter["name"] in values
            }
        )
    else:
        workflow_step = next(
            item
            for group in templates[entrypoint]["steps"]
            for item in group
            if item.get("template") == step
        )
        inputs.update(
            {
                parameter["name"]: parameter["value"]
                for parameter in workflow_step.get("arguments", {}).get(
                    "parameters", []
                )
            }
        )
    replacements = {
        "{{inputs.parameters." + key + "}}": value for key, value in inputs.items()
    }
    replacements.update(
        {"{{workflow.parameters." + key + "}}": value for key, value in values.items()}
    )
    replacements.update(
        {
            "{{workflow.name}}": workflow_name,
            "/workspace": str(tmp_path),
            "$(PREPARATION_BUCKET)": "datasets",
            "$(PREPARATION_S3_ENDPOINT_URL)": "http://cold-storage.example.test",
            "$(PREPARATION_REGION)": "test",
            "$(PREPARATION_SERVER_MEDIA_ROOT)": "/fiftyone-preparation",
        }
    )
    args = list(container["args"])
    for source, replacement in replacements.items():
        args = [argument.replace(source, replacement) for argument in args]
    assert all("{{" not in argument and "$(" not in argument for argument in args)
    return importlib.import_module(Path(container["command"][1]).stem), args


@pytest.mark.parametrize("policy", [None, "warn"], ids=["default-strict", "warn"])
def test_workflow_preparation_duplicate_policy(
    tmp_path, s3_provider, monkeypatch, policy
):
    module, args = preparation_command(
        tmp_path, "bypass-test", **({"duplicate-conflicts": policy} if policy else {})
    )

    content = io.BytesIO()
    Image.new("RGB", (3, 2), "gray").save(content, format="TIFF")
    keys = [
        "raw/collection/Amaranthus albus/ColorChecker.tiff",
        "raw/collection/Amaranthus palmeri/ColorChecker.tiff",
    ]
    for key in keys:
        s3_provider.objects["datasets", key] = content.getvalue()
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


def test_workflow_skip_retry_and_resume_in_a_new_submission(
    tmp_path, s3_provider, monkeypatch, caplog
):
    keys = [f"raw/collection/A/{number}.png" for number in range(3)]
    for number, key in enumerate(keys):
        content = io.BytesIO()
        Image.new("RGB", (100, 80), (number * 60, 10, 20)).save(content, format="PNG")
        data = content.getvalue()
        s3_provider.objects["datasets", key] = data[:41] if number == 1 else data
    module, args = preparation_command(
        tmp_path, "first-run", **{"invalid-images": "skip"}
    )
    storage = s3_provider.storage
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    read = storage.read_image

    async def interrupted_read(bucket, key):
        if key == keys[2]:
            raise BlobStorageError("interrupted download")
        return await read(bucket, key)

    reader = AsyncMock(side_effect=interrupted_read)
    monkeypatch.setattr(storage, "read_image", reader)
    with pytest.raises(BlobStorageError, match="interrupted download"):
        module.main(args)
    assert not (Path(args[0]) / "index.coco.json").exists()
    reader.side_effect = read
    reader.reset_mock()
    module.main(args)
    assert [call.args[1] for call in reader.call_args_list] == keys[1:]
    first = json.loads((Path(args[0]) / "index.coco.json").read_text())
    assert len(first["images"]) == 2
    assert first["info"]["preparation"]["skipped_images"][0]["raw_key"] == keys[1]

    reader.reset_mock()
    s3_provider.client.put_object.reset_mock()
    caplog.clear()
    module, args = preparation_command(
        tmp_path,
        "new-run",
        **{"invalid-images": "skip", "resume-run-id": "first-run"},
    )
    module.main(args)
    reader.assert_awaited_once_with("datasets", keys[1])
    s3_provider.client.put_object.assert_not_called()
    assert json.loads((Path(args[0]) / "index.coco.json").read_text()) == first
    assert "new-run/prepared" in args[0]
    assert any(keys[1] in message for message in caplog.messages)


def test_direct_audit_uses_previous_index_and_keeps_its_report(
    tmp_path, s3_provider, monkeypatch
):
    content = io.BytesIO()
    Image.new("RGB", (4, 3), "red").save(content, format="PNG")
    s3_provider.objects["datasets", "raw/collection/A/seed.png"] = content.getvalue()
    prepare, args = preparation_command(tmp_path, "previous-run")
    monkeypatch.setattr(prepare, "create_storage", lambda *a, **k: s3_provider.storage)
    prepare.main(args)
    previous = tmp_path / "previous-run" / "prepared"
    old_report = previous / "checksum-audit.json"
    old_report.write_text("existing report")
    audit, args = preparation_command(
        tmp_path,
        "audit-run",
        step="audit-checksums",
        entrypoint="audit-checksums",
        **{"resume-run-id": "previous-run"},
    )
    monkeypatch.setattr(audit, "create_storage", lambda *a, **k: s3_provider.storage)
    audit.main(args)
    assert args[0] == str(previous / "index.coco.json")
    assert old_report.read_text() == "existing report"
    report = tmp_path / "audit-run" / "prepared" / "checksum-audit.json"
    assert json.loads(report.read_text())["status"] == "passed"
    _, overridden = preparation_command(
        tmp_path,
        "another-audit",
        step="audit-checksums",
        entrypoint="audit-checksums",
        **{"resume-run-id": "different-run", "index-run-id": "previous-run"},
    )
    assert overridden[0] == str(previous / "index.coco.json")
    _, full = preparation_command(
        tmp_path,
        "full-run",
        step="audit-checksums",
        **{"resume-run-id": "previous-run", "index-run-id": "previous-run"},
    )
    assert full[0] == str(tmp_path / "full-run/prepared/index.coco.json")
    _, missing = preparation_command(
        tmp_path,
        "missing-audit",
        step="audit-checksums",
        entrypoint="audit-checksums",
        **{"resume-run-id": "missing-run"},
    )
    with pytest.raises(audit.AuditFailure):
        audit.main(missing)
    failed_report = tmp_path / "missing-audit/prepared/checksum-audit.json"
    assert json.loads(failed_report.read_text())["status"] == "failed"
    assert old_report.read_text() == "existing report"


def test_workflow_checksum_audit_runs_before_prelabel(
    tmp_path, s3_provider, monkeypatch
):
    spec = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2]
            / "workflows/preparation-workflow-template.yaml"
        ).read_text()
    )["spec"]
    steps = next(t for t in spec["templates"] if t["name"] == "prepare-for-review")[
        "steps"
    ]
    assert [step[0]["template"] for step in steps] == [
        "prepare-images",
        "audit-checksums",
        "prelabel",
        "register-for-review",
        "approve-checkpoint-cleanup",
        "cleanup-checkpoints",
    ]
    _, prelabel_args = preparation_command(
        tmp_path,
        "new-run",
        step="prelabel",
        **{
            "model-revision": "test-model",
            "resume-run-id": "original-run",
            "index-run-id": "another-run",
        },
    )
    assert prelabel_args[prelabel_args.index("--checkpoint-dir") + 1] == str(
        tmp_path / "original-run" / "prepared" / "prelabel-checkpoints"
    )
    assert prelabel_args[0] == str(
        tmp_path / "new-run" / "prepared" / "index.coco.json"
    )
    content = io.BytesIO()
    Image.new("RGB", (4, 3), "red").save(content, format="PNG")
    key = "raw/collection/A/seed.png"
    s3_provider.objects["datasets", key] = content.getvalue()
    prepare, args = preparation_command(tmp_path, "audit-run")
    monkeypatch.setattr(prepare, "create_storage", lambda *a, **k: s3_provider.storage)
    prepare.main(args)
    audit, args = preparation_command(tmp_path, "audit-run", step="audit-checksums")
    monkeypatch.setattr(audit, "create_storage", lambda *a, **k: s3_provider.storage)
    audit_template = next(
        t for t in spec["templates"] if t["name"] == "audit-checksums"
    )
    workspace = next(
        mount
        for mount in audit_template["container"]["volumeMounts"]
        if mount["name"] == "workspace"
    )
    assert not workspace.get("readOnly", False)
    audit.main(args)
    report_path = Path(args[0]).with_name("checksum-audit.json")
    assert json.loads(report_path.read_text())["status"] == "passed"
    s3_provider.objects["datasets", key] = b"corrupted"
    png_key = json.loads(Path(args[0]).read_text())["images"][0]["file_name"]
    s3_provider.objects["datasets", png_key] = b"also corrupted"
    with pytest.raises(audit.AuditFailure):
        audit.main(args)
    report = json.loads(report_path.read_text())
    assert report["status"] == "failed"
    assert {issue["key"] for issue in report["issues"]} == {key, png_key}


def test_prelabel_entrypoint_uses_the_previous_run_index(
    tmp_path, s3_provider, monkeypatch
):
    content = io.BytesIO()
    Image.new("RGB", (4, 3), "red").save(content, format="PNG")
    s3_provider.objects["datasets", "raw/collection/A/seed.png"] = content.getvalue()
    prepare, prepare_args = preparation_command(tmp_path, "audited-run")
    audit, audit_args = preparation_command(
        tmp_path, "audited-run", step="audit-checksums"
    )
    storage = s3_provider.storage
    for module in (prepare, audit, s3_storage):
        monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    prepare.main(prepare_args)
    audit.main(audit_args)
    previous = tmp_path / "audited-run" / "prepared"
    index = (previous / "index.coco.json").read_bytes()
    assert json.loads((previous / "checksum-audit.json").read_text())["status"] == (
        "passed"
    )

    calls = []
    prelabel, args = preparation_command(
        tmp_path,
        "prelabel-run",
        step="prelabel",
        entrypoint="prelabel",
        **{"resume-run-id": "audited-run", "model-revision": "test-model"},
    )
    monkeypatch.setattr(
        prelabel,
        "Sam3Predictor",
        lambda *args: (
            lambda image: calls.append(image.size) or Prediction([[1, 1, 3, 3]])
        ),
    )
    prelabel.main(args)
    assert args[0] == str(previous / "index.coco.json")
    assert args[args.index("--checkpoint-dir") + 1] == str(
        previous / "prelabel-checkpoints"
    )
    assert calls == [(4, 3)]
    assert (previous / "index.coco.json").read_bytes() == index
    output = tmp_path / "prelabel-run" / "prepared"
    assert not (output / "index.coco.json").exists()
    assert not (output / "checksum-audit.json").exists()
    assert len(json.loads((output / "draft.coco.json").read_text())["annotations"]) == 1

    calls.clear()
    prelabel, args = preparation_command(
        tmp_path,
        "second-prelabel-run",
        step="prelabel",
        entrypoint="prelabel",
        **{"resume-run-id": "audited-run", "model-revision": "test-model"},
    )
    prelabel.main(args)
    assert not calls
    assert (tmp_path / "second-prelabel-run/prepared/draft.coco.json").exists()

    prelabel, args = preparation_command(
        tmp_path,
        "other-run",
        step="prelabel",
        entrypoint="prelabel",
        **{
            "resume-run-id": "checkpoint-run",
            "index-run-id": "audited-run",
            "model-revision": "test-model",
        },
    )
    assert args[0] == str(previous / "index.coco.json")
    assert args[args.index("--checkpoint-dir") + 1] == str(
        tmp_path / "checkpoint-run" / "prepared" / "prelabel-checkpoints"
    )
    prelabel.main(args)
    assert calls == [(4, 3)]
    assert (tmp_path / "other-run/prepared/draft.coco.json").exists()
    _, default_args = preparation_command(
        tmp_path,
        "current-run",
        step="prelabel",
        entrypoint="prelabel",
        **{"model-revision": "test-model"},
    )
    assert default_args[0] == str(
        tmp_path / "current-run" / "prepared" / "index.coco.json"
    )
    prelabel, missing_args = preparation_command(
        tmp_path,
        "missing-index-run",
        step="prelabel",
        entrypoint="prelabel",
        **{"resume-run-id": "unknown-run", "model-revision": "test-model"},
    )
    with pytest.raises(FileNotFoundError, match="unknown-run"):
        prelabel.main(missing_args)
    assert not (tmp_path / "missing-index-run/prepared/draft.coco.json").exists()


def test_registration_entrypoint_selects_previous_draft(
    tmp_path, draft_coco, monkeypatch
):
    previous = tmp_path / "prelabel-run" / "prepared" / "draft.coco.json"
    previous.parent.mkdir(parents=True)
    previous.write_text(json.dumps(draft_coco))
    registration, args = preparation_command(
        tmp_path,
        "registration-run",
        step="register-for-review",
        entrypoint="register-for-review",
        **{"resume-run-id": "prelabel-run", "dataset-name": "review"},
    )
    observed = []

    def register(name, labels, media_root):
        observed.append((name, json.loads(labels.read_text()), media_root))

    monkeypatch.setenv("FIFTYONE_DATABASE_URI", "mongodb://example.test")
    monkeypatch.setattr(registration, "register_fiftyone", register)
    registration.main(args)
    assert args[1] == str(previous)
    assert observed == [("review", draft_coco, "/fiftyone-preparation")]
    assert not (tmp_path / "registration-run/prepared/draft.coco.json").exists()

    _, override = preparation_command(
        tmp_path,
        "other-run",
        step="register-for-review",
        entrypoint="register-for-review",
        **{
            "resume-run-id": "checkpoint-run",
            "draft-run-id": "prelabel-run",
            "dataset-name": "review",
        },
    )
    assert override[1] == str(previous)
    registration.main(override)
    assert observed == [("review", draft_coco, "/fiftyone-preparation")] * 2
    _, full = preparation_command(
        tmp_path,
        "current-run",
        step="register-for-review",
        **{
            "resume-run-id": "prelabel-run",
            "draft-run-id": "prelabel-run",
            "dataset-name": "review",
        },
    )
    assert full[1] == str(tmp_path / "current-run/prepared/draft.coco.json")
    _, default = preparation_command(
        tmp_path,
        "current-run",
        step="register-for-review",
        entrypoint="register-for-review",
        **{"dataset-name": "review"},
    )
    assert default[1] == str(tmp_path / "current-run/prepared/draft.coco.json")
    _, missing = preparation_command(
        tmp_path,
        "missing-registration-run",
        step="register-for-review",
        entrypoint="register-for-review",
        **{"resume-run-id": "unknown-run", "dataset-name": "review"},
    )
    with pytest.raises(FileNotFoundError, match="unknown-run"):
        registration.main(missing)
    assert len(observed) == 2


def test_registration_entrypoint_imports_previous_draft(
    tmp_path, draft_coco, fiftyone, review_name
):
    previous = tmp_path / "prelabel-run" / "prepared" / "draft.coco.json"
    previous.parent.mkdir(parents=True)
    previous.write_text(json.dumps(draft_coco))
    registration, args = preparation_command(
        tmp_path,
        "registration-run",
        step="register-for-review",
        entrypoint="register-for-review",
        **{"resume-run-id": "prelabel-run", "dataset-name": review_name},
    )
    registration.main(args)
    dataset = fiftyone.load_dataset(review_name)
    assert len(dataset) == len(draft_coco["images"])
    sample = dataset.first()
    assert sample.filepath.startswith("/fiftyone-preparation/png/detection/")
    sample["prelabel_reason"] = "reviewed"
    sample.save()
    with pytest.raises(ValueError, match="already exists"):
        registration.main(args)
    assert fiftyone.load_dataset(review_name).first()["prelabel_reason"] == "reviewed"
    assert json.loads(previous.read_text()) == draft_coco


def test_workflow_compatible_resume_preserves_provenance_and_cleanup_isolation(
    tmp_path, s3_provider, monkeypatch
):
    for number in range(2):
        content = io.BytesIO()
        Image.new("RGB", (4, 3), (number * 100, 10, 20)).save(content, format="PNG")
        s3_provider.objects["datasets", f"raw/collection/A/{number}.png"] = (
            content.getvalue()
        )
    prepare, first_prepare = preparation_command(
        tmp_path, "first-run", **{"code-revision": "revision-a"}
    )
    audit, first_audit = preparation_command(
        tmp_path, "first-run", step="audit-checksums"
    )
    prelabel, first_prelabel = preparation_command(
        tmp_path,
        "first-run",
        step="prelabel",
        **{"code-revision": "revision-a", "model-revision": "weights-a"},
    )
    storage = s3_provider.storage
    reader = AsyncMock(wraps=storage.read_image)
    monkeypatch.setattr(storage, "read_image", reader)
    for module in (prepare, audit, s3_storage):
        monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    for module in (prepare, prelabel):
        monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.0"))

    calls = []

    def interrupt(image):
        calls.append(image.size)
        if len(calls) == 2:
            raise RuntimeError("interrupted inference")
        return Prediction([[1, 1, 3, 3]])

    monkeypatch.setattr(prelabel, "Sam3Predictor", lambda *args: interrupt)
    prepare.main(first_prepare)
    audit.main(first_audit)
    with pytest.raises(RuntimeError, match="interrupted inference"):
        prelabel.main(first_prelabel)

    options = {
        "resume-run-id": "first-run",
        "index-run-id": "different-run",
        "code-revision": "revision-b",
        "model-revision": "weights-a",
    }
    for module in (prepare, prelabel):
        monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.1"))
    calls.clear()
    monkeypatch.setattr(
        prelabel,
        "Sam3Predictor",
        lambda *args: (
            lambda image: calls.append(image.size) or Prediction([[1, 1, 3, 3]])
        ),
    )
    _, next_prepare = preparation_command(tmp_path, "second-run", **options)
    _, next_audit = preparation_command(
        tmp_path, "second-run", step="audit-checksums", **options
    )
    _, next_prelabel = preparation_command(
        tmp_path, "second-run", step="prelabel", **options
    )
    assert next_prelabel[0] == str(
        tmp_path / "second-run" / "prepared" / "index.coco.json"
    )
    reader.reset_mock()
    s3_provider.client.put_object.reset_mock()
    prepare.main(next_prepare)
    reader.assert_not_awaited()
    s3_provider.client.put_object.assert_not_called()
    audit.main(next_audit)
    assert reader.await_count == 4
    reader.reset_mock()
    prelabel.main(next_prelabel)
    assert len(calls) == 1
    assert reader.await_count == 1

    prepared = tmp_path / "second-run" / "prepared"
    result = json.loads((prepared / "draft.coco.json").read_text())
    assert result["info"]["preparation"]["code_revision"] == "revision-b"
    assert result["info"]["prelabel"]["model_identity"] == "sam3"
    assert {
        (image["prelabel_project_version"], image["prelabel_code_revision"])
        for image in result["images"]
    } == {("0.2.0", "revision-a"), ("0.2.1", "revision-b")}
    assert all(
        source["preparation"]
        == {"project_version": "0.2.0", "code_revision": "revision-a"}
        for image in result["images"]
        for source in image["sources"]
    )
    assert json.loads((prepared / "checksum-audit.json").read_text())["status"] == (
        "passed"
    )
    first_root = tmp_path / "first-run" / "prepared"
    shared = {
        path: path.read_bytes()
        for name in ("preparation-checkpoints", "prelabel-checkpoints")
        for path in (first_root / name).rglob("*")
        if path.is_file()
    }
    objects = dict(s3_provider.objects)
    assert len(shared) == 4
    assert cleanup_checkpoints(tmp_path, "second-run") == 0
    assert all(path.read_bytes() == data for path, data in shared.items())
    assert cleanup_checkpoints(tmp_path, "first-run") == 4
    assert all(not path.exists() for path in shared)
    assert (first_root / "index.coco.json").is_file()
    assert (first_root / "checksum-audit.json").is_file()
    assert (prepared / "draft.coco.json").is_file()
    assert s3_provider.objects == objects


def test_cleanup_workflows_require_approval_and_target_only_the_selected_run():
    workflows = Path(__file__).resolve().parents[2] / "workflows"
    preparation = yaml.safe_load(
        (workflows / "preparation-workflow-template.yaml").read_text()
    )["spec"]
    templates = {template["name"]: template for template in preparation["templates"]}
    steps = templates["prepare-for-review"]["steps"]
    assert [step[0]["template"] for step in steps[-3:]] == [
        "register-for-review",
        "approve-checkpoint-cleanup",
        "cleanup-checkpoints",
    ]
    assert templates["approve-checkpoint-cleanup"]["suspend"] == {}
    for step in steps[-2:]:
        parameters = step[0]["arguments"]["parameters"]
        assert parameters == [{"name": "run-name", "value": "{{workflow.name}}"}]
    container = templates["cleanup-checkpoints"]["container"]
    assert container["args"] == ["/workspace", "{{inputs.parameters.run-name}}"]
    assert "envFrom" not in container
    assert not next(
        mount for mount in container["volumeMounts"] if mount["name"] == "workspace"
    ).get("readOnly", False)

    standalone = yaml.safe_load(
        (workflows / "preparation-cleanup-workflow-template.yaml").read_text()
    )["spec"]
    cleanup_steps = standalone["templates"][0]["steps"]
    assert [step[0]["templateRef"]["template"] for step in cleanup_steps] == [
        "approve-checkpoint-cleanup",
        "cleanup-checkpoints",
    ]
    for step in cleanup_steps:
        assert step[0]["templateRef"]["name"] == "nachet-preparation"
        assert step[0]["arguments"]["parameters"] == [
            {"name": "run-name", "value": "{{workflow.parameters.run-name}}"}
        ]


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
        parameter["name"]: parameter["value"]
        for parameter in spec["arguments"]["parameters"]
        if "value" in parameter
    }
    values.update(
        {
            "raw-prefix": "raw/collection",
            "code-revision": "test-revision",
            "dataset-name": review_name,
            "draft-run-id": "different-run",
            "model-revision": "synthetic-weights",
            "duplicate-conflicts": "error",
        }
    )
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
        template = templates[name]
        container = template["container"]
        workflow_step = next(
            item
            for group in templates["prepare-for-review"]["steps"]
            for item in group
            if item.get("template") == name
        )
        inputs = {
            parameter["name"]: parameter["value"]
            for parameter in workflow_step.get("arguments", {}).get("parameters", [])
        }
        environment = {}
        for entry in container.get("env", []):
            ref = entry["valueFrom"]["configMapKeyRef"]
            environment[entry["name"]] = config_maps[ref["name"]][ref["key"]]
        for source in container.get("envFrom", []):
            environment.update(secrets[source["secretRef"]["name"]])
        args = []
        for value in container["args"]:
            for key, replacement in inputs.items():
                value = value.replace("{{inputs.parameters." + key + "}}", replacement)
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

    for step in templates["prepare-for-review"]["steps"][:4]:
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
        assert source["preparation"]["code_revision"] == "test-revision"
        assert sample.prelabel_code_revision == "test-revision"
        assert (
            sample.prelabel_project_version == source["preparation"]["project_version"]
        )
        assert len(sample.draft_boxes.detections) == 1
    before = dict(s3_provider.objects)
    for name in ("prepare-images", "prelabel"):
        run_step(name)
    assert s3_provider.objects == before
    workspace_files = {
        p.name for p in (tmp_path / "workspace").rglob("*") if p.is_file()
    }
    assert {
        "index.coco.json",
        "draft.coco.json",
        "checksum-audit.json",
        "preparation.sqlite3",
    } <= workspace_files
    assert (
        len(
            list(
                (tmp_path / "workspace").rglob(
                    "prelabel-checkpoints/releases/*/*/*.json"
                )
            )
        )
        == 3
    )
    with pytest.raises(ValueError, match="already exists"):
        run_step("register-for-review")
    assert len(fiftyone.load_dataset(review_name)) == 3

# Reviewed dataset releases (MLOps)

The dataset release component implements the reviewed-data handoff described in
[the October 20 draft of #895](https://github.com/ai-cfia/nachet/issues/895#issuecomment-6303217149).
It runs after PNG preparation and FiftyOne review. Blob storage holds the dataset
files and version snapshots; the database registers their identity and readiness.

This is a standalone uv project under `mlops/datasets/`. Its publisher, blob
adapter, database registry, migration, readers, tests and examples are all owned
by MLOps and do not import the backend application. The current external detector script,
`nachetmodel/HFTrainer_detector_2026012601_js.py` in `nachet-model-ccds`, is unchanged.
The storage-aware record reader is its integration point, described below.

Storage providers come from the standalone `nachet-blob` project in
[`mlops/blob`](../blob/README.md), installed as a local editable dependency.
Its `mlops_blob` module is a temporary copy of `backend/app/blob/`.
`DatasetController` uses `BlobStorageAdapter`, which delegates to that module's
`BlobStorageInterface` and S3/Azure implementations. The original standalone
S3 upload/download implementation has been replaced. See
[the copy's provenance and differences](../blob/mlops_blob/README.md) for the future
extraction into `nachet/common`; the backend source remains unchanged.

Keep `mlops/blob/` beside `mlops/datasets/` when checking out, copying or mounting
the source for a job. `uv sync --locked` installs both projects. The dataset
wheel contains only `dataset_release`; deployments that install wheels must
also supply the standalone `nachet-blob` wheel.

## Files and registration

```text
<dataset bucket>/
  png/detection/<sha256>.png          # prepared full images, uploaded beforehand
  png/classification/<sha256>.png     # crops generated during publication
  releases/<name>/<version>/
    coco.json                        # reviewed labels and fixed image splits
    release.json                     # v1 release manifest and crop relationships
```

The hash rule is SHA-256 of the exact saved file bytes, including PNG encoding.
The component rejects a detection PNG whose bytes do not match its filename.
JSON is saved as UTF-8 with sorted object keys, compact separators and finite
numbers. Array order is part of the release identity. A SHA-256 of `release.json`
is recorded in the database; the manifest does not contain its own hash.

`release.json` is the companion format chosen for this implementation. It records
the release UUID, name, version, author, UTC creation time, input-request hash,
conversion recipe, crop recipe, reviewed COCO checksum, image inventory and crop
relationships. Each crop identifies its COCO image, annotation, category, split,
pixel rectangle, blob key, size and checksum. The containing manifest supplies
the dataset version. Metadata remains readable without mirroring all COCO boxes
into application annotation or object rows.

The `dataset_release` table contains one registration per `(name, version)`:
its UUID, author, creation time, container, request hash, manifest location/hash
and `staging` or `ready` status. Membership, labels and crop mappings remain in
the blob snapshot. On PostgreSQL it lives in a dedicated `nachet_datasets` schema
by default, with its own `dataset_release_version` migration-version table.
The registry does not change the backend schema or its Alembic head.
Application picture identifiers can be retained as extra COCO provenance fields;
the standalone publisher does not query or create application picture records.

## Prepare a release specification

Use the structure in `examples/dataset-release.json`. Replace its example
hash and dimensions with a real prepared PNG reference and its image dimensions.
The file describes inputs; it does not upload or convert the source images.

Required inputs include the dataset name/version, author, conversion code
revision/settings and reviewed COCO. Every image needs an explicit `split` of
`train`, `validation` or `test`. COCO `file_name` must be the existing
`png/detection/<sha256>.png` key within the selected container.

Add source records to `images[].sources` when known. Multiple records preserve
original paths, collection dates, species, batch and tray information for shared
image bytes. Additional COCO and source attributes are preserved. Supply a
globally consistent `specimen_group` when photographs represent the same known
specimen. Identical image keys and known specimen groups must not cross splits.
Unknown specimen identity cannot be detected from metadata alone; assign splits
upstream using the available collection knowledge.

Set `generate_crops` to `true` to publish a classifier-ready release. The cropper
uses the reviewed COCO boxes, not pre-labeling predictions or live MongoDB state.
COCO decimal coordinates remain unchanged. Pixel extraction uses floor for
left/top and ceil for right/bottom, converts to RGB and saves PNG at compression
level 6. The recipe includes its algorithm ID and Pillow version. Each crop
inherits its parent's split. Unchanged crop bytes reuse the same blob key.

## Run

Run from `mlops/datasets/`. Install the locked standalone dependencies:

```bash
uv sync --locked
```

Set `DATASET_DATABASE_URL` to an explicit async connection URL, such as
`postgresql+psycopg://<user>:<password>@<host>/<database>`. The default PostgreSQL
schema is `nachet_datasets`; `DATASET_REGISTRY_SCHEMA` can select another existing
schema dedicated to MLOps. Provision that schema and its role permissions before
running the migration. A local SQLite registry can use
`sqlite+aiosqlite:///dataset-registry.local` and needs no schema.

Load these settings from the job environment, `.env`, or a `DATASET_ENV_FILE`.
Apply the standalone migration explicitly before publication:

```bash
uv run alembic -c alembic.ini upgrade head
```

This runs only the MLOps registry migration `a895d501ea01`; it does not run the
backend migrations. Argo CD is not configured to invoke it automatically.
The publication command never creates tables, schemas, buckets or permissions.

```bash
uv run python -m dataset_release --container training-datasets \
  publish examples/dataset-release.json

uv run python -m dataset_release --container training-datasets \
  inspect reviewed-seeds v1

uv run python -m dataset_release --container training-datasets \
  validate reviewed-seeds v1 --expected-manifest-sha256 <saved-manifest-sha256>
```

`DATASET_BLOB_PROVIDER` selects `s3` (the default) or `azure`.
For S3, use boto3's standard AWS credentials/role providers or supply
`S3_ACCESS_KEY` and `S3_SECRET_KEY` together. Optional settings are
`S3_REGION_NAME`, `S3_ENDPOINT_URL`, `S3_USE_SSL` and `S3_VERIFY`.
Temporary explicit credentials also accept `S3_SESSION_TOKEN`.
`AWS_ENDPOINT_URL_S3`, `AWS_REGION` and `AWS_DEFAULT_REGION` are also supported. The S3
adapter performs conditional writes and checksums without importing `app.blob`.

For Azure, set `DATASET_BLOB_PROVIDER=azure` and
`AZURE_STORAGE_CONNECTION_STRING`. Use an existing container and the same
publish/inspect/validate commands. The copied Azure provider uses the SDK's
non-overwriting upload and translates conflicts into the common blob exception.
The database settings, release format and training reader contract are the same
for both providers. For library use, pass a copied provider to
`BlobStorageAdapter(create_blob_storage_client(provider, config))`, or use
`BlobStorageAdapter.from_environment()`; this replaces the former `S3Storage`
helper. Close the adapter when the job finishes.

The commands output JSON containing the dataset UUID, version, manifest
location/hash and the value to store in `Model.dataset`. `inspect` also returns
image/annotation/crop counts and split counts. Both `inspect` and `validate`
verify every referenced file, so inspection performs dataset reads.

## Publication, retries and retention

Publication reserves the name/version with a database unique constraint before
writing blobs. Conflicting inputs under that identity fail. Identical retries
reuse the reservation and stored objects. A failure leaves the row in `staging`;
readers refuse it. Retry the same specification to complete the operation.
If the specification itself must change, use another version identity.

The controller checks images, labels, dimensions, boxes and crop relationships,
writes the reviewed COCO and manifest with overwrite disabled, verifies the
stored bytes, then commits `ready` and the final manifest hash. Only registered
`ready` releases can be resolved. Reads verify the saved hashes and fail on
missing or changed inputs. A correction in FiftyOne must be exported as a new
version, which can continue sharing unchanged PNGs with earlier versions.

S3 `overwrite=False` now uses an atomic `If-None-Match: *` PUT, rather than a
separate existence check. The chosen S3 service must support conditional writes;
publication fails if it does not. A concurrent S3 conditional-write conflict can
be retried with the same specification. No operation silently falls back to an
overwriting upload.

Use a dedicated dataset bucket and publisher credentials. Grant trainers only
read access to the relevant objects and release registrations. Restrict writes
to the dataset publisher and enforce retention/no deletion of referenced files
with storage policy or object lock as appropriate. Application database RBAC
does not protect direct S3 reads. Code protects writes made through this module;
it cannot prevent an unrelated administrator from replacing objects or editing
database rows. Checksums detect such changes. Database registration backups and
blob backups/retention are separate operational requirements. Deletion and
garbage collection are intentionally absent, including cleanup of failed-upload
objects. Argo execution location and its credentials/mounts are not deployed here.

## Training integration

`dataset_release.reader.ReleasedDataset` resolves a verified release and fetches
detector images or classifier crops one at a time through the MLOps blob adapter. It does
not require a shared FiftyOne PVC or create a permanent local image collection.
Full verification at open reads the entire release; each later sample read also
verifies its checksum. Measure those reads and representative training epochs
before introducing a cache or staging layer. Blocking provider reads/writes run in
worker threads so they do not block the asynchronous controller.

```python
from dataset_release.reader import ReleasedDataset

# controller is a DatasetController configured with the job's BlobStorageAdapter,
# standalone registry session factory and dataset container.
reader = await ReleasedDataset.open(
    controller, "reviewed-seeds", "v1", expected_manifest_sha256=saved_hash
)
reference = reader.training_reference({"max_train_samples": 32})

async for record in reader.detector_records("train"):
    # record: image_id, image={path, bytes}, width, height, objects={id, area,
    # bbox, category}; category IDs are zero-based in sorted COCO-ID order.
    consume(record)

async for record in reader.classifier_records("validation"):
    # record: image={path, bytes}, label, image_id, annotation_id, release ID.
    consume(record)
```

The detector records match the fields produced by the current script's
`load_coco_as_hf_dataset()`. HuggingFace `datasets.Image` accepts the image bytes
representation. The external adapter must build each split separately and keep
the full version category mapping. The reader retains negative images with no
boxes, which the legacy loader currently drops. It does not apply class filters,
reject lists, random splits or sample limits; any deliberate training subset
must be recorded in `dataset_run_settings` and preserve the version's splits.

Log the returned reference with MLflow; retain it with checkpoints and evaluation
reports, require the saved manifest hash on resume/evaluation, and pass
`reference['model_dataset']` into model registration's existing `Model.dataset`
field. The manifest fixes split membership, so its hash pins the splits too.
The external trainer's random-split and validation-as-test fallback must not be
used for release inputs. This implementation provides the reader and reference
contract; it does not change that external trainer or automatically wire MLflow.

## Validation

From `mlops/datasets/`:

```bash
uv run pytest
```

Provider tests run separately from `mlops/blob/` with `uv run pytest`.
Dataset adapter and publication/reader integration tests remain in this project.
The dataset CI job also runs when the sibling blob project changes.

Set `NACHET_MODEL_CCDS` to the local `nachet-model-ccds` checkout to enable the
compatibility test against its actual `nachetmodel/coco_to_hf_dataset.py`.
Run `uv sync --locked --group compatibility` to install that optional check's
HuggingFace dependency. It is not needed by the release publisher.
That test compares labels, decimal boxes and decoded pixels in all three saved
splits. Without the variable, only that external compatibility test is skipped.

The suite exercises publication, interrupted uploads, identical and conflicting
retries, concurrent publishers, corrected versions, missing/corrupt files,
provenance, split leakage, crop dimensions, negative detection images, the
additive migration and atomic S3 request behavior. It also publishes and recovers
releases through the actual copied S3/Azure providers using fake SDK transports.
It uses temporary SQLite databases and in-memory object stores; it does not establish production S3/Azure
compatibility, live PostgreSQL deployment, GPU training quality or throughput.

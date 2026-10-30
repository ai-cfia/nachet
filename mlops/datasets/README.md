# Reviewed dataset releases (MLOps)

The dataset release component implements the reviewed-data handoff described in
[the October 20 draft of #895](https://github.com/ai-cfia/nachet/issues/895#issuecomment-6303217149).
It runs after PNG preparation and FiftyOne review. Blob storage holds the dataset
files and version snapshots; the database registers their identity and readiness.

This is a standalone uv project under `mlops/datasets/`. Its command, exporter,
readers, registry migration, integration tests and examples consume the separate
[`DatasetController` package](../DatasetController/README.md). The controller owns
release publication, validation, contracts, blob adaptation, registry mapping and
configuration. Both projects are owned by MLOps and do not import the backend
application. The current external detector script,
`nachetmodel/HFTrainer_detector_2026012601_js.py` in `nachet-model-ccds`, is unchanged.
The storage-aware record reader is its integration point, described below.

Storage providers come from the standalone `nachet-blob` project in
[`mlops/blob`](../blob/README.md), installed through the controller dependency.
Its `mlops_blob` module is a temporary copy of `backend/app/blob/`.
`DatasetController` uses `BlobStorageAdapter`, which delegates to that module's
`BlobStorageInterface` and S3/Azure implementations. The original standalone
S3 upload/download implementation has been replaced. See
[the copy's provenance and differences](../blob/PROVENANCE.md) for the future
extraction into `nachet/common`; the backend source remains unchanged.

Keep `mlops/DatasetController/` and `mlops/blob/` beside `mlops/datasets/` when
checking out, copying or mounting the source for a job. `uv sync --locked`
installs all three projects. The dataset wheel contains only `dataset_release`;
deployments that install wheels must also supply `nachet-dataset-controller` and
`nachet-blob` wheels. Import the facade with
`from dataset_controller import DatasetController, ReleaseSpec`.

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

### Export reviewed FiftyOne labels without copying images

The exporter uses FiftyOne's [labels-only COCO API](https://docs.voxel51.com/api/fiftyone.utils.coco.html)
with `export_media=False`. It writes JSON only. Full images must already exist
in the publisher's container at `png/detection/<sha256>.png`.

Run the export in the annotation environment with FiftyOne installed and access
to its dataset database. Install this project and its sibling blob package in
that environment if needed, using its Python interpreter from `mlops/datasets/`:

```bash
python -m pip install -e ../blob -e ../DatasetController -e .
```

FiftyOne is deliberately not a publisher dependency. Use the annotation
environment's existing FiftyOne version; the offline preparation and publishing
commands do not require it. This script does not deploy a job or connect to a
cluster on its own.

Before exporting, give each selected FiftyOne sample an explicit `split` field
containing `train`, `validation` or `test`. An optional `sha256` field identifies
the exact stored PNG bytes. If absent, a `<sha256>.png` filename supplies the
hash; other filenames require reading and hashing the local file without
converting it. The publisher subsequently verifies the actual blob bytes.
An optional `sources` field is a list of source dictionaries described above.
If absent, the exporter records the sample filepath and FiftyOne sample ID.
`--split-field`, `--sha256-field` and `--sources-field` select other field names.
The detection field must contain corrected `Detections`; use an empty
`Detections` for a reviewed negative image. Image dimensions must be available
in FiftyOne metadata or readable from the local media by FiftyOne.

Copy `examples/release-metadata.json` to a working file and set the release
name/version, author, and the revision/settings used to prepare the PNGs.
It contains release metadata only, without a `coco` field. Export the reviewed
dataset, or restrict it to a saved reviewed view:

```bash
python -m dataset_release.fiftyone_export \
  --dataset seeds --view reviewed --label-field corrected_detections \
  --release-metadata release-metadata.json --output-dir reviewed-v1
```

Omit `--view` to export the entire dataset. Pause edits to the selected samples
while exporting; this reads the dataset and does not lock the annotation UI.
The view must retain the split/hash/source fields needed for the handoff.

The new output folder contains `coco.json` and `dataset-release.json`. COCO
image paths are replaced with blob keys, and each image includes `sha256`,
`split` and `sources`. Image/annotation/category IDs, reviewed boxes and extra
COCO attributes are retained. Export joins use full paths rather than basenames;
missing, duplicate or conflicting membership fails preparation. The output
folder must not already exist. Crops are disabled for this handoff.

If COCO has already been exported, prepare it without connecting to FiftyOne:

```bash
uv run python -m dataset_release.fiftyone_export \
  --coco labels.json --membership membership.json \
  --release-metadata release-metadata.json --output-dir reviewed-v1
```

`membership.json` is a JSON list with exactly one record per exported image:

```json
[
  {
    "file_name": "/datasets/reviewed/seed.png",
    "sha256": "replace-with-the-64-character-lowercase-png-sha256",
    "split": "train",
    "sources": [{ "original_path": "collection/tray/seed.tiff" }]
  }
]
```

`file_name` must match the corresponding exported COCO path, including its
directories; slash direction is normalized. `sources` can be omitted to retain
sources already in COCO. The optional explicit COCO `sha256` field is validated
against its blob key. Older releases without that field retain their serialized
shape and remain compatible with identical publication retries.

Publish the prepared specification using the existing database/blob settings
and registry provisioning described below:

```bash
uv run python -m dataset_release --container training-datasets \
  publish reviewed-v1/dataset-release.json
```

`DatasetController.publish()` writes `coco.json`, the release manifest and its
database registration. It downloads existing PNGs for integrity/dimension
checks, without copying or uploading those images. This requires the existing
registry migration; no additional database migration is needed for export.

Set `generate_crops` to `true` to publish a classifier-ready release. The cropper
uses the reviewed COCO boxes, not pre-labeling predictions or live MongoDB state.
COCO decimal coordinates remain unchanged. Pixel extraction uses floor for
left/top and ceil for right/bottom, converts to RGB and saves PNG at compression
level 6 using OpenCV. The recipe includes its algorithm ID and OpenCV version.
Each crop inherits its parent's split. Unchanged crop bytes reuse the same blob key.

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
Standalone controller and crop tests run from `mlops/DatasetController/` with
`uv run python -I -m pytest`.
Dataset adapter and publication/reader integration tests remain in this project.
The controller and dataset CI jobs also run when either sibling package changes.

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

# Reviewed dataset releases (MLOps)

This standalone project prepares, publishes and reads reviewed training datasets.
The database owns release metadata, image membership and reviewed labels. Blob
storage holds the prepared detection PNGs and generated classification crops.
`DatasetController` generates COCO, membership, metadata and manifest JSON from
those database records when requested. JSON exports are outputs, not separately
maintained release inputs.

The publisher, registry, migrations, readers and tests belong to MLOps and do not
import the backend application. The external detector trainer is unchanged; the
reader is its integration point.

Storage providers come from the standalone `nachet-blob==0.1.0` project in
[`mlops/blob`](../blob/README.md), installed as a local editable dependency.
Its `blob` module is a temporary copy of `backend/app/blob/`.
`DatasetController` uses `BlobStorageAdapter`, which delegates to that module's
`BlobStorageInterface` and S3/Azure implementations. Dataset-specific extensions
in `dataset_release/providers/` preserve atomic create-only publication, SDK
credential-chain support, Azure connection strings, and connection/stream cleanup.
They use inheritance while leaving the reviewed shared `blob` package unchanged.
The worker adapter keeps synchronous SDK calls off the controller event loop. See
[the copy's provenance and differences](../blob/PROVENANCE.md) for the future
extraction into `nachet/common`; the backend source remains unchanged.

Keep `mlops/blob/` beside `mlops/datasets/` when checking out, copying or mounting
the source for a job. `uv sync --locked` installs both projects. The dataset
wheel contains `dataset_release` and its `utility` helpers; deployments that
install wheels must also supply the matching standalone `nachet-blob` wheel.
The dataset project explicitly declares the Azure Core, boto3, botocore, and
Loguru dependencies used by its provider extensions.

Run `uv sync --locked` and `uv run --no-sync python -I -m pytest` from this
directory. The provider publication/readback tests construct both S3 and Azure
adapters through `BlobStorageAdapter.from_environment()`, using deterministic
SDK transports. CI additionally builds and installs both wheels in a separate
environment, checks dependency compatibility, and runs `tests/check_install.py`
to verify provider inheritance and the CLI without backend or legacy imports.
These local checks do not contact live storage services.

## Database entities and files

| Entity | Stored information |
| --- | --- |
| `dataset_release` | Name/version, author, description, dates, previous version, PNG conversion revision/settings, crop option/recipe, reviewed COCO categories/annotations and extra attributes, statistics, status and checksums. |
| `dataset_membership` | Release reference, image order and COCO ID, exact exported filename, PNG SHA-256, dimensions, split, sources, extra image attributes and verified byte size. |
| `dataset_crop` | Release reference, annotation ID, output order, pixel rectangle, crop SHA-256 and byte size. Image, category and split are derived from reviewed labels and membership. |

COCO categories, annotations and extensible source attributes retain their JSON
structure in database columns. The release metadata fields and per-image
membership are stored as entities rather than repeated inside a stored release
specification. Array order is preserved because it contributes to release identity.
Images with identical PNG bytes can retain separate COCO IDs and provenance.

```text
<dataset bucket>/
  png/detection/<sha256>.png          # prepared images, uploaded beforehand
  png/classification/<sha256>.png     # crops generated during publication
```

New releases do not upload `coco.json` or `release.json`. Their familiar
`releases/<name>/<version>/...` keys identify generated documents; they are not
physical blob locations. Use the controller or the `export` command to obtain
them. The existing manifest hash and training-reference fields remain available
for pinning and integrity checks.

Registrations created before migration `c83f26d5ea02` retain their original blob
snapshots and hashes. They are marked `database_backed=false` and continue to be
read through the legacy snapshot path. The migration does not copy old JSON into
new entities or rewrite blobs. Complete old staging releases with the previous
runtime, or its original `ReleaseSpec` through the library API, before retiring
that workflow. New releases use the database workflow below.

## Migration runbook

Run from `mlops/datasets/` and install the locked dependencies:

```bash
uv sync --locked
```

Set `DATASET_DATABASE_URL` to an explicit async SQLAlchemy URL, such as
`postgresql+psycopg://<user>:<password>@<host>/<database>`. PostgreSQL defaults to
schema `nachet_datasets`; `DATASET_REGISTRY_SCHEMA` can select another existing
MLOps schema. Provision its role and permissions beforehand. Local testing can
use `sqlite+aiosqlite:///dataset-registry.local` without a schema.
Settings load from the environment, `.env`, or `DATASET_ENV_FILE`.

Before upgrading an existing registry:

1. Stop publisher/preparation jobs and back up the registry database. Retain the
   existing dataset blobs for legacy releases.
2. Confirm the selected registry and current revision:

   ```bash
   uv run alembic -c alembic.ini current
   ```

3. Apply the standalone migrations:

   ```bash
   uv run alembic -c alembic.ini upgrade head
   uv run alembic -c alembic.ini current
   ```

   Expect revision `c83f26d5ea02`. It follows `a895d501ea01`, extends
   `dataset_release`, allows `draft` status, and creates `dataset_membership` and
   `dataset_crop`. Existing registrations remain intact and use their legacy
   snapshot path. No blob reads or writes occur during migration.
4. Check the tables in the selected MLOps schema, then validate an existing ready
   release with its saved manifest hash before restarting jobs.

These commands run only the standalone MLOps migration history, not backend
migrations. Argo CD does not invoke them automatically. Publication does not
create schemas, tables, buckets or permissions. This change has not been applied
to a live server.

Downgrading to `a895d501ea01` is supported only while no database-backed releases
exist. Once new entities have been created, downgrading would discard the source
of truth; the migration refuses it. Roll back by restoring the pre-upgrade backup
and previous runtime instead. Do not delete new rows merely to bypass that guard.

## Create release metadata

Register metadata once in the database, using CLI options or
`DatasetController.create_release(ReleaseDefinition(...))`:

```bash
uv run python -m dataset_release --container training-datasets \
  create reviewed-seeds v1 --author reviewer \
  --conversion-revision <image-preparation-revision> \
  --setting format=PNG --setting mode=RGB \
  --description "Reviewed seed images" --dataset-cutoff-date 2026-11-02
```

`--setting KEY=VALUE` accepts a JSON value or plain text. Record the actual
revision/settings used to prepare the PNGs. Optional `--previous-version` records
a prior-version reference. `--generate-crops` enables classification crops at
publication; detection-only is the default. Creation reserves a unique name and
version with status `draft`. There is no metadata JSON input or template to keep
in sync.

The dataset curator assigns `train`, `validation` or `test` before preparation.
Known `specimen_group` values must not span splits. Neither the exporter nor the
publisher invents splits or specimen identities. PNG hashes identify the exact
saved file bytes, including PNG encoding. The publisher verifies those bytes
against `png/detection/<sha256>.png` in the selected container.

## Prepare reviewed labels

Choose one input workflow for the draft release. Both save reviewed labels and
membership atomically in the database. IDs, decimal boxes, negative images,
extra annotation attributes and source provenance are preserved.

### From FiftyOne

Run in the annotation environment with FiftyOne installed and access to its
dataset database, the MLOps registry, and the local media when hashing or image
metadata requires it. FiftyOne is intentionally not a publisher dependency.
Install the two sibling packages using the annotation interpreter if needed:

```bash
python -m pip install -e ../blob -e .
python -m dataset_release.fiftyone_export \
  --container training-datasets --name reviewed-seeds --version v1 \
  --dataset seeds --view reviewed --label-field corrected_detections
```

Omit `--view` to use the full dataset. Retain the split/hash/source fields in the
saved view. Every selected sample needs an explicit `split` and reviewed
`Detections`; use empty `Detections` for reviewed negatives. Optional `sha256`
identifies the stored PNG bytes. Otherwise a `<sha256>.png` filename supplies the
hash, or the script hashes the exact local file bytes. Optional `sources` is a
list of provenance records. If absent, the original path and FiftyOne sample ID
are recorded. Use `--split-field`, `--sha256-field` and `--sources-field` for other
field names. Image dimensions must be in FiftyOne metadata or readable from media.

The exporter writes only temporary labels with `export_media=False` and
`abs_paths=True`, then saves the resulting membership and labels in SQL. It
does not copy images. Pause annotation edits during export; the script does not
lock the FiftyOne App. Register the draft metadata before starting the export.

### From an existing web COCO export

Register each image's verified exported filename, PNG hash, split and optional
provenance using `add-image` or the catalog's `add_membership` API. For example:

```bash
uv run python -m dataset_release --container training-datasets \
  add-image reviewed-seeds v1 --file-name /datasets/reviewed/seed.png \
  --sha256 <64-character-png-sha256> --split train \
  --original-path collection/tray/seed.tiff --specimen-group seed-1

uv run python -m dataset_release.fiftyone_export \
  --container training-datasets --name reviewed-seeds --version v1 \
  --coco labels.json
```

Repeat `add-image` for every exported image. Bulk callers can add each
`ImageMembership` through the catalog API without authoring a membership JSON
file. Reviewed COCO must match the registered paths exactly except for slash
direction. Missing, duplicated or conflicting membership fails preparation;
matching does not fall back to basename or image order.

For the web App's `@voxel51/io/export_samples`, choose Labels only, COCO, the
reviewed field and Absolute paths. The [upstream I/O plugin](https://github.com/voxel51/fiftyone-plugins/blob/main/plugins/io/__init__.py)
defaults Absolute paths to false. Inspect `images[].file_name` in the actual
export before registering membership. If the export rewrites paths, register a
verified mapping using the actual exported names or re-export with absolute
paths. The deployed App behavior still needs live verification.

A draft can be re-prepared with corrected labels for the same membership.
Membership additions stop after labels are prepared. Publication freezes the
release: further changes require a new version.

## Publish and request JSON

Publish the prepared database release by name and version:

```bash
uv run python -m dataset_release --container training-datasets \
  publish reviewed-seeds v1
uv run python -m dataset_release --container training-datasets \
  inspect reviewed-seeds v1
uv run python -m dataset_release --container training-datasets \
  validate reviewed-seeds v1 --expected-manifest-sha256 <saved-manifest-sha256>
```

The controller derives label statistics from reviewed COCO and stores them with
the release: bounding-box/class availability, class count, and counts of images
with one or multiple reviewed objects. Negative images count in neither object
count. `inspect` returns these statistics, descriptive metadata and split counts.

Generate JSON only when a consumer needs it:

```bash
uv run python -m dataset_release --container training-datasets \
  export reviewed-seeds v1 metadata
uv run python -m dataset_release --container training-datasets \
  export reviewed-seeds v1 membership
uv run python -m dataset_release --container training-datasets \
  export reviewed-seeds v1 coco --output coco.json
uv run python -m dataset_release --container training-datasets \
  export reviewed-seeds v1 manifest --output release.json
```

`metadata`, `membership`, `spec` and prepared `coco` documents can be exported from
a draft. A manifest requires a ready release and validates the referenced files.
`--output` refuses to overwrite a file. Without it, JSON goes to stdout.
The Python API is `await controller.export_json(name, version, document)`.
The FiftyOne preparation command also accepts an optional `--output-dir` to
request generated COCO/spec files. These exports can be discarded and regenerated;
they do not become publication inputs. `create`, `add-image`, preparation and
metadata/membership/spec/COCO exports need database access only, without blob
credentials for database-backed releases.

## Storage, publication and retries

`DATASET_BLOB_PROVIDER` selects `s3` (default) or `azure`. S3 uses boto3's standard
credential/role providers or explicit `S3_ACCESS_KEY` and `S3_SECRET_KEY` together.
Optional settings are `S3_REGION_NAME`, `S3_ENDPOINT_URL`, `S3_USE_SSL`, `S3_VERIFY`
and `S3_SESSION_TOKEN`; `AWS_ENDPOINT_URL_S3`, `AWS_REGION` and
`AWS_DEFAULT_REGION` are also supported. Azure uses
`AZURE_STORAGE_CONNECTION_STRING`. Close the adapter when a library job finishes.
Use an existing container and provide publisher access for publication and file
validation.

Publication locks and changes the draft to `staging`, fixing the request hash and
crop recipe before expensive work. It verifies existing detection PNG bytes and
dimensions, optionally writes crops, records verified sizes and crop lineage,
generates the manifest, validates its files, then commits `ready` and the manifest
checksum. Detection-only publication writes no blobs. JSON is UTF-8 with sorted
keys, compact separators and finite numbers. COCO array order is preserved.

Crop generation uses reviewed boxes, floors left/top and ceils right/bottom,
converts to RGB, and saves PNG at compression level 6 using OpenCV. Its recorded
recipe pins the algorithm and OpenCV version. Each crop inherits the image's
split. Unchanged PNG bytes reuse their blob key.

A failed publication remains `staging` and cannot be read for training. Retry
`publish <name> <version>` to finish it; identical concurrent publishers reuse the
same registration and content. Conflicting inputs require another version.
New releases reconstruct documents from database entities and check the recorded
manifest hash on read. Legacy releases continue checking their saved blob JSON.
Missing/corrupted PNGs or altered published records fail validation.

Crop writes use atomic non-overwriting storage operations. S3 requires support
for `If-None-Match: *`; conditional conflicts can be retried without overwriting.
Grant trainers read access to the registry and dataset objects; restrict writes
to publishers. Database backups are now essential for new release metadata,
membership and labels, while blob retention protects PNG bytes and legacy
snapshots. Direct administrator edits can bypass application locks; saved hashes
detect changes on read. Deletion, garbage collection, live migration application
and cluster job deployment are outside these tools.

## Training integration

Python jobs publish or resume a specification with
`DatasetController.publish_release(spec)`. Use
`get_release_registration(name, version)` to read registry state, including staging
registrations, and `load_verified_release(name, version, expected_manifest_sha256)`
to verify a ready release and return its registration, manifest and reviewed COCO.

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
database migrations and atomic S3 request behavior. It also publishes and recovers
releases through the actual copied S3/Azure providers using fake SDK transports.
It uses temporary SQLite databases and in-memory object stores; it does not establish production S3/Azure
compatibility, live PostgreSQL deployment, GPU training quality or throughput.

## Argo release and smoke workflows

`../workflows/dataset-release-workflow-template.yaml` defines
`nachet-dataset-release`. It publishes an existing prepared release, passes the
returned manifest SHA-256 to a separate validation pod, and exposes
`dataset-reference` and `manifest-sha256` output parameters. Submission is the
explicit publication action; the template does not create drafts, assign splits,
export a live FiftyOne view, or run migrations. Use the preparation commands above
before submitting it.

`nachet-dataset-release-smoke` creates four tiny PNGs with separate train,
validation and test membership, a reviewed negative image, two non-contiguous
category IDs and three classification crops. It tests exact export-path matching,
provenance, decimal boxes, category mapping, crop pixels, and saved splits. It
removes one image to prove publication stays incomplete, restores it, then calls
the **same release template** to finish publication. It checks identical retries,
immutable inputs, split leakage, wrong manifest pins and corrupt bytes.

The smoke run uses `dataset-smoke-<workflow UUID>/v1` and an `onExit` cleanup pod.
Cleanup removes only that run's generated fixture keys and SQL entities, including
after partial preparation. Fixture pixels and crop hashes differ between runs.
The report is available in the workflow's `report` output and verify-pod logs;
the temporary release reference stops being usable after cleanup.

### Provision the runtime

Both templates use namespace `argo-workflows` and service account `argo-workflow`,
and are included in the existing Kustomize bundle. Howard's Argo CD application
owns deployment from Git; do not manually apply these templates there. A merge
deploys templates but does not submit runs.

The image build uses the `mlops` context so `datasets` and `blob` stay siblings:

```bash
docker build -f mlops/datasets/Dockerfile -t nachet-dataset-release:local mlops
```

The smoke helper lives in `../workflows/scripts/dataset_release_smoke.py`.
The Dockerfile copies it to `/opt/workflows/scripts/dataset_release_smoke.py`;
it is not part of the dataset release wheel. The build runs the dataset tests
before producing the non-root runtime.
`.github/workflows/mlops-datasets-build.yml` builds and signs
`ghcr.io/ai-cfia/nachet-dataset-release` using the existing PR, commit, branch and
version tag patterns. The workflow's `image` parameter accepts a PR tag or digest
to test the intended code rather than the default `main` image.

Provision the existing bucket and standalone registry using the migration runbook
above. Provide a Kubernetes Secret named `nachet-dataset-release` containing:

- `DATASET_DATABASE_URL` and, for PostgreSQL, `DATASET_REGISTRY_SCHEMA`.
- `DATASET_BLOB_PROVIDER` (`s3` or `azure`) and its storage settings documented
  above. For Howard/Ceph, explicitly set `S3_ENDPOINT_URL` or
  `AWS_ENDPOINT_URL_S3`; `MLFLOW_S3_ENDPOINT_URL` is not a release setting.
- The S3 credentials/role configuration or `AZURE_STORAGE_CONNECTION_STRING`.

Create a **separate** `nachet-dataset-release-smoke` Secret targeting a test
registry/schema and an existing dedicated bucket named `nachet-dataset-smoke`
or `nachet-dataset-smoke-<suffix>`. Smoke credentials need object read, write,
overwrite and delete permissions, and registry insert, update, select and delete
permissions. The smoke command refuses other bucket names. Run the same standalone
migrations against that test registry before its first run. Neither template
creates tables, schemas, buckets or Secrets, and this change does not provision
Howard resources.

### Submit a run

After the image and templates are deployed:

```bash
argo submit --namespace argo-workflows \
  --from workflowtemplate/nachet-dataset-release \
  --parameter dataset-name=reviewed-seeds \
  --parameter dataset-version=v1 \
  --parameter container=training-datasets

argo submit --namespace argo-workflows \
  --from workflowtemplate/nachet-dataset-release-smoke \
  --parameter 'image=ghcr.io/ai-cfia/nachet-dataset-release:<PR-number>' \
  --parameter container=nachet-dataset-smoke
```

`credentials-secret` can select another provisioned Secret. Keep smoke credentials
restricted to the test registry and bucket. Inspect the verify report and cleanup
pod, not just whether publication succeeded. Stopping a run allows its exit
handler to run; terminating it skips exit handlers. If cleanup cannot complete,
use the **same image, Secret environment, container and workflow UUID** to retry:

```bash
python /opt/workflows/scripts/dataset_release_smoke.py \
  --container nachet-dataset-smoke \
  --name dataset-smoke-<workflow-UUID> cleanup
```

CI checks Argo syntax, Kustomize rendering, hash propagation, cleanup wiring, and
the fixture lifecycle with SQLite and fake S3/Azure SDK transports. A successful
submitted smoke run additionally proves connectivity and behavior against the
selected live registry/object store. It does not test live FiftyOne export,
trainer integration or GPU model quality.

The smoke lifecycle tests live in
`../workflows/tests/test_dataset_release_smoke.py`. They explicitly load the same
provider fixture plugin as the dataset tests from
`../test_support/dataset_blob_fixtures.py`. From the repository root, run them
with the dataset project's environment and pytest configuration:

```bash
uv run --project mlops/datasets --no-sync python -I -m pytest \
  -c mlops/datasets/pyproject.toml \
  mlops/workflows/tests/test_dataset_release_smoke.py -q
```

The configuration adds the shared test-support directory to pytest's import
path. The image's checks stage mounts both test directories and the shared
fixtures, runs them together, and omits all test files from the runtime image.

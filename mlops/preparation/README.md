# Dataset preparation

Convert a seed-image collection into SHA-256-named PNGs and a COCO image index
for pre-labeling and review. Use `prepare_s3.py` for originals in S3, or
`prepare_images.py` for a local collection. Run these Python 3.12 commands from
the repository root.

Conversion, pre-labeling, checksum auditing, and FiftyOne sample metadata updates
log progress at the next item boundary after each five-minute interval.

```bash
uv sync --project mlops/preparation --locked
```

## Convert originals from S3

`prepare_s3.py` lists and reads originals under `raw/` using the exact S3 keys,
converts each image in memory and uploads it to `png/detection/<sha256>.png` in
the same bucket. It uses the local converter's settings and source records.
Neither originals nor generated PNGs are saved locally.

```bash
CODE_REVISION=$(git rev-parse HEAD)
uv sync --project mlops/preparation --locked --group storage
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_s3.py /work/prepared \
  --bucket training-datasets --endpoint-url https://s3.example.test \
  --region us-east-1 --raw-prefix raw/collection-01 \
  --code-revision "$CODE_REVISION"
```

The S3 keys below the collection prefix must follow the species/split layout
described below. Source paths stay relative to that prefix. Empty species
folders are retained when the listing includes directory markers for them.
Pass original keys with spaces and punctuation unchanged; boto3 handles URL
encoding. Do not percent-encode or decode keys before passing them to the SDK.
Preparation retains the exact original key in source metadata.
The index records hashes of the original bytes read; it does not require
ingestion-specific hash metadata. Originals must already be in S3 and remain
unchanged during a run.

The final `index.coco.json` is saved in the output directory only after every
non-skipped source succeeds. On failure, already uploaded PNGs remain in S3; a retry uses the same
hash keys. Without checkpointing it rereads and converts the originals.
Use a new output directory for a changed collection.

### Resume interrupted S3 preparation

Pass `--resume` to persist progress in
`output_root/preparation-checkpoints/<project-version>/preparation.sqlite3`.
Each source is committed only after its PNG upload succeeds (or its identical
PNG has already been uploaded). Rerun the same command and output directory to
reconstruct the index from completed records without downloading, converting
or uploading those sources again. An upload interrupted before its checkpoint
commit is safely retried using the same hash key.

To resume into a new output directory, pass
`--checkpoint-dir /work/previous-run/prepared` instead. This reads and extends
the earlier checkpoint while writing the final index into the new output
directory. A checkpoint directory is created if absent; logs show its path and
the number of completed sources. Preserve it on persistent storage, and use only
one writer at a time.

The endpoint, region, bucket, prefix, source-key listing, split and duplicate
policy must match the checkpoint. Mismatches fail explicitly.
Original object bytes and previously uploaded PNGs **must remain unchanged**:
resume does not download them to verify their contents. Start with a new
checkpoint if those bytes change or prepared PNGs are removed.
Skipped invalid images are not marked completed: every retry rechecks and logs
them, and strict mode will still reject them. The invalid-image policy may
therefore change between retries. Local collection conversion does not
checkpoint.

### Checkpoint versions and provenance

Preparation and pre-label checkpoints record `[project].version` from
`pyproject.toml`. An older checkpoint can be reused by the same major version,
except that versions below `1.0.0` must also have the same minor version. A
checkpoint from a newer release is never reused. SemVer prerelease precedence
applies; build metadata does not change precedence. Incompatible versions
start separate checkpoints and leave existing progress untouched.

Integer-version checkpoints from older runs are not reused or automatically
deleted. A new run must process that work again. Cleanup requires approval as
described below. Compatible checkpoints may be reused across different
`--code-revision` labels: each checkpointed source records its producer in
`sources[].preparation.project_version` and `sources[].preparation.code_revision`.
`info.preparation.code_revision` identifies the run assembling the index, not
necessarily every source's producer.

Release maintainers must bump the compatibility boundary for checkpoint or
output changes that cannot safely reuse prior results: the minor version while
below `1.0.0`, and the major version afterward. Code and model revision labels
are operator-supplied, not verified against the images or weights.

All writers to `png/detection/` must use the PNG byte hash as the filename. The
uploader requests create-only writes, but some S3-compatible stores ignore that
condition and upload the same bytes again on retries. It does not read back
existing PNGs or protect against a writer that puts other bytes under a hash key.

### Audit S3 checksums

After preparation, `audit_s3.py` downloads each indexed PNG and every indexed
original, including all sources of duplicate PNGs, and compares their SHA-256
hashes with the index. It also checks that each PNG key matches its hash.
The audit collects malformed records, missing or unreadable objects and checksum
mismatches while continuing to check the remaining valid records. It logs each
issue and fails after completing the checks if any issues were found.
Only indexed images are checked; invalid images skipped during preparation are
not audited. This is a point-in-time check, so originals and PNGs must remain
unchanged afterward. It rereads every indexed object and adds S3 traffic.

By default, the audit atomically writes `checksum-audit.json` beside the input
index, even when validation finds issues. `--report-path` selects another
location. In Argo the report always belongs to the current run:
`/workspace/<workflow-name>/prepared/checksum-audit.json`. The report contains
the bucket, `checked_pngs` and `checked_sources` (objects successfully read
and hashed, including mismatches), and an `issues` list. Each issue includes
a code, its location in the index, the object key when available, and a
message; checksum mismatch messages include expected and actual hashes.
`status` is `passed` or `failed` when the audit completes. It is `incomplete`
if the audit was interrupted or could not finish. An interrupted or unexpected
failure may leave an incomplete report without all the issues found so far;
check the step logs as well. Each retry replaces the report with its own result.

```bash
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/audit_s3.py /work/prepared/index.coco.json \
  --bucket training-datasets --endpoint-url https://s3.example.test \
  --region us-east-1
```

Install the storage group as for S3 preparation; use `--allow-http` only for a
trusted HTTP endpoint. The audit logs its PNG and source totals on success.

The COCO source records do not create database mappings.

Credentials come from the AWS credential chain. For a private CA, set
`AWS_CA_BUNDLE`. Use `--allow-http` only with a trusted HTTP endpoint.

## Collection layout

Species folders sit directly under the collection or inside a split folder.
Each species folder's name becomes a COCO category. Split folders named
`Training`/`Train`, `Validation`/`Val` or `Test`/`Testing` are recognized in any
case. Species folders directly under the collection stay unassigned.

```text
Collection/
  Training/
    Avena fatua/batch-01/tray-a/a.tiff
  Validation/
    Avena fatua/b.tiff
  Zea mays/
    new-image.jpg
```

Images are found recursively under each species folder, so batch and tray
folders stay in the recorded path. Hidden files and folders are skipped, as are
files that are not TIFF, JPEG or PNG. An image directly under the collection or
a split folder is an error.

Split folders directly inside a species folder are rejected; check that you
passed the collection itself, not its parent. Species names that differ only
in case are also rejected.

## Convert and index

Set `CODE_REVISION` to the source revision used for conversion.

```bash
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_images.py \
  /work/raw/Collection /work/prepared \
  --raw-prefix raw/Collection --code-revision "$CODE_REVISION"
```

The output directory must be outside the collection. It receives
`index.coco.json` and `png/detection/<sha256>.png`.

In the example, the two Avena images keep their train and validation splits and
the Zea image gets `split: null`. The command never creates a random split. If
a collection has no split folders but belongs to one split, pass
`--split train`, `validation` or `test`. `--split` is refused when split folders
are present.

All images go into one index with one category list, so category IDs are the
same across splits. IDs are only meaningful within one index; match separately
generated indexes by category name.

## Conversion

Raw files are never modified. PNG inputs are copied byte for byte. TIFF and JPEG
conversion uses the research script's OpenCV `IMREAD_UNCHANGED` flag and default
PNG encoding. Both 16-bit grayscale and 16-bit RGB TIFFs keep their depth.
Converted files follow OpenCV's colour handling and do not copy ICC profiles.
Grayscale TIFFs with alpha, signed pixel values, multi-frame images and TIFF
samples above 16 bits fail with the filename.

### Opt-in invalid-image skipping

Both conversion commands accept `--invalid-images skip`; the default
`--invalid-images error` still stops at the first unreadable image.
Skip mode never enables Pillow's truncated-image recovery or uploads rejected
image bytes. Each decode/encode failure emits a WARNING containing the source path
(the full raw key for S3) and error. The final index records these paths and errors
in `info.preparation.skipped_images`, and the processing summary includes
`skipped_sources`. Valid images keep their normal hashes and source records.
An entirely invalid collection still fails without publishing an index.

Read/download/upload failures, duplicate conflicts and unsupported conversion
policies (such as multi-frame images) remain fatal. Skip mode is not a storage
error bypass.

PNG names are the SHA-256 of the PNG bytes, so an encoder change can
rename the PNG for an unchanged raw image.

## Index contents

Each image records `image_sha256`, the SHA-256 of its PNG bytes. This is the
same hash used in `file_name`; it identifies the PNG rather than the raw file.

Each image's `sources` list records `original_path` relative to the collection,
the species, the raw file's SHA-256 and its legacy MD5. Batch, tray and specimen
meaning is not inferred from folder names. With `--raw-prefix`, each source
also gets `raw_key`, the expected S3 key under `raw/`. The command does not
upload files or check whether those keys exist in S3.

Identical PNGs share one image record and keep every source path. Identical
PNGs with different species or different splits fail by default, which stops
an exact duplicate from appearing in both training and validation. Different
photographs of the same specimen are not detected.

### Temporary duplicate-conflict bypass

Both conversion commands accept `--duplicate-conflicts warn` to temporarily
continue past conflicting species or splits, for example when reference
ColorChecker images occur under multiple species. The default is
`--duplicate-conflicts error`; reference images are not automatically excluded.

```bash
# Local collection
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_images.py /work/raw/Collection /work/prepared \
  --code-revision "$CODE_REVISION" --duplicate-conflicts warn

# Existing S3 collection
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_s3.py /work/prepared \
  --bucket training-datasets --endpoint-url https://s3.example.test \
  --region us-east-1 --raw-prefix raw/collection-01 \
  --code-revision "$CODE_REVISION" --duplicate-conflicts warn
```

In warn mode only, sources are processed in sorted relative POSIX-path order
in both local and S3 preparation. Identical PNGs still have one image record,
one hash-based key and all original source records. The first source's split
is retained, even when a later source has a different split. Original files
and S3 keys are not changed.

**This is a temporary bypass, not label reconciliation.** Pre-labeling and
FiftyOne still use the first source's species. Conflicting species remain
ambiguous, and conflicting splits are not reconciled. Review these images
before using the results for training; omit the option to restore strict checks.

The conversion CLIs emit timestamped INFO/WARNING logs to stderr, captured by
Argo. INFO logs show source discovery, the selected policy and processing totals
for sources, unique PNGs, duplicate sources and skipped sources. Per-image
processing, saved/uploaded or reused PNGs, and resumed sources are DEBUG logs
and are not shown at the CLIs' default INFO level. Enabling the bypass emits a
warning, and each conflict logs the PNG hash, both paths, species and splits,
and the retained values. Existing final summaries remain on stdout. Failures
still stop the run and retain their traceback, except decode/encode failures
explicitly opted into `--invalid-images skip`.

Outputs can be regenerated: a rerun that produces the same bytes succeeds, and a
run that would change an existing file fails. Use a new output directory when
the collection or settings change.

## Pre-label with SAM3

`prelabel.py` adds draft boxes to the COCO index for review in FiftyOne.
Install the `sam3` group and provide the local SAM3 Transformers snapshot
directory. Set `MODEL_REVISION` to the snapshot's revision label.

```bash
uv sync --project mlops/preparation --locked --group sam3
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prelabel.py /work/prepared/index.coco.json \
  /work/prepared /work/draft.coco.json \
  --model-path /models/sam3 --model-revision "$MODEL_REVISION" --device cuda
```

For PNGs already in S3, install the `storage` group as well and pass the bucket
root instead of a local media directory:

```bash
uv sync --project mlops/preparation --locked --group sam3 --group storage
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prelabel.py /work/prepared/index.coco.json \
  s3://training-datasets /work/draft.coco.json \
  --endpoint-url https://s3.example.test --region us-east-1 \
  --model-source "s3://${MODEL_BUCKET}/base/sam3_hf_transformers" \
  --model-path /work/models/sam3_hf_transformers \
  --model-revision "$MODEL_REVISION" --device cuda
```

Set `MODEL_BUCKET` to the bucket containing the snapshot. With `--model-source`,
pre-labeling downloads the snapshot into `--model-path` using the supplied
endpoint, region and S3 credentials. The completed snapshot stays in that
directory and is reused for the same source and revision.

S3 input reads one PNG into memory and checks its key and SHA-256 before
decoding. A missing object, hash mismatch or dimension mismatch stops the run.
PNGs are not saved locally. The bucket root contains the `png/detection/` keys
from COCO; a key prefix in the S3 media-root argument is refused. Credentials
and private-CA settings are described under "Convert originals from S3".

For each image, the command tries the notebook's prompts in order:
"foreground object", "thick long seed", then "insect". It stops at the first
prompt returning 1 to 9 boxes. Boxes keep the species recorded in the index.
Padding follows the notebook: `p` pixels on the left and top, `2p` on the
right and bottom, clipped to the image. `--padding` sets `p` (default: 3).

The Python `prelabel()` function accepts a `predictor(image)` callable returning
`Prediction(boxes, prompt=None)`. Boxes use pixel XYXY coordinates. SAM3 handles
its prompts internally; other predictors can leave `prompt` unset. The CLI
currently loads SAM3.

CUDA uses BF16 autocast and TF32; CPU uses FP32. `--model-revision` is a label
you choose for the weights, recorded in `info.prelabel`.

To resume pre-labeling, append
`--checkpoint-dir /work/prelabel-checkpoints --code-revision "$CODE_REVISION"`.
Completed images are committed individually and reused on retry; an interrupted
image is processed again. Before inference on a fresh run, the CLI saves an
initial COCO snapshot with every image marked `unannotated` (for example,
`draft.coco.unannotated.json` for `draft.coco.json`). A run with matching
per-image checkpoints skips the snapshot. The final draft is written only
after all images finish. Checkpoints are scoped to the index, media location,
model identity and revision, device, padding and inference policy. When the same
model path can refer to different models, also set a distinct `--model-identity`.
When supplied, it is recorded in `info.prelabel.model_identity`. Checkpointed
Python callers must supply `predictor_identity` and `code_revision`; S3 callers
must also supply a stable `storage_identity` for the endpoint and region.
If a checkpoint contains the legacy `draft` status, restart with a fresh
checkpoint directory.

Reused images are not read again by pre-labeling. Keep their media unchanged;
the Argo checksum audit rechecks the indexed S3 objects before pre-labeling.
Checkpointed image records include `prelabel_project_version` and
`prelabel_code_revision` for the original producer, even when a later
compatible release assembles the draft. On resume, saved boxes with an empty
status are checked for overlap.

Each image records its `prelabel_status`, `prelabel_prompt` and
`prelabel_reason`. The prompt is the last one attempted, or `null` if
the predictor does not use prompts or inference was skipped.

| Status | Reason | Meaning |
| --- | --- | --- |
| `unannotated` | `null` | Initial snapshot before inference. |
| `null` | `null` | A prompt returned 1 to 9 valid boxes with no shared area. |
| `needs_review` | `nested_boxes` | One padded box lies inside another. |
| `needs_review` | `overlapping_boxes` | Padded boxes share area without containment. |
| `needs_review` | `no_detections` | All prompts failed the count check; the last returned no boxes. |
| `needs_review` | `too_many_detections` | All prompts failed the count check; the last returned at least 10 boxes. |
| `needs_review` | `invalid_boxes` | A prompt returned 1 to 9 boxes, but invalid geometry was dropped. |
| `needs_review` | `high_bit_depth` | High-bit image; inference skipped pending a normalization policy. |

Use `needs_review` to find images flagged during pre-labeling. The command
refuses an index that already has annotations. Without `--checkpoint-dir`, an
interrupted run starts again from the beginning. To assemble a new draft from
checkpoints when an older completed draft already exists, choose a new output
path.

## Register for review

`register_fiftyone.py` imports the draft COCO into a new persistent FiftyOne
dataset. It reads only the COCO file. Set `--server-media-root` to the path
where the FiftyOne server can read the `png/detection/...` files; the import
worker does not need access to that path. The command does not copy or upload
images.

```bash
uv sync --project mlops/preparation --locked --group fiftyone
export FIFTYONE_DATABASE_URI='<mongo-uri>'
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/register_fiftyone.py collection-01-review \
  /work/draft.coco.json --server-media-root /srv/datasets
```

Use the server's MongoDB URI and, if customized, `FIFTYONE_DATABASE_NAME`.
The command requires `FIFTYONE_DATABASE_URI` and refuses an implicit local
database. Every imported sample gets the `not-verified` tag. Draft boxes go in
`boxes_YYYYMMDD`, using the UTC registration date. Every imported label gets
the `not-verified` tag. When the draft records the model snapshot and
revision, each box also gets a `<model-name>-<model-revision>` label tag. The
name is the final component of the S3 model source or local model directory.
Source records, split assignments and the pre-label fields described above
stay on each sample. `source_species`
copies the first source's species for filtering, or stays `null` when it is
unknown. It records the original species separately from reviewed box labels.
`object_key` keeps the PNG key, and `image_sha256` copies its hash from the
COCO image record. Each input image must include this field; the import does
not read image bytes to recalculate it. Raw-file hashes stay in `sources`.
`dataset.info` keeps the COCO `info` block.
Images imported from an older prepared index without `prelabel_status` get
`unannotated`. An explicit `null` is kept as an empty status.

Existing dataset names are refused so a rerun cannot overwrite review work.
An import uses a temporary `preparation-import-*` name and renames the dataset
only after success. A caught failure deletes that temporary dataset. A killed
process can leave it behind, but a retry uses a new temporary name. Remove a
leftover only after confirming its job has stopped; keep review datasets.

## Runtime images

The Dockerfile uses `mlops/` as its build context. The `cpu` target contains
conversion and upload commands, `sam3` adds CUDA-enabled PyTorch and
pre-labeling, and `registration` adds the FiftyOne SDK. Tests run during the
build without network access. Weights and credentials are supplied at runtime.

```bash
docker build --platform linux/amd64 -f mlops/preparation/Dockerfile \
  --target cpu -t nachet-preparation-cpu:local mlops
docker build --platform linux/amd64 -f mlops/preparation/Dockerfile \
  --target sam3 -t nachet-preparation-sam3:local mlops
docker build --platform linux/amd64 -f mlops/preparation/Dockerfile \
  --target registration -t nachet-preparation-registration:local mlops
```

The SAM3 build checks for a CUDA-enabled PyTorch and the required SAM3 classes.
Actual GPU execution depends on the cluster's NVIDIA driver and model weights.
Published images are `ghcr.io/ai-cfia/nachet-preparation-{cpu,sam3,registration}`.
Use an immutable image tag or digest for a workflow run.
Copy each published digest from the CPU, SAM3 and registration builds in one
successful Actions run into `CPU_IMAGE`, `SAM3_IMAGE` and `REGISTRATION_IMAGE`.
Set `CODE_REVISION` to that run's checked-out commit. Pull-request builds use
the tested merge commit, which can differ from the PR head.

## Argo workflow

`mlops/workflows/preparation-workflow-template.yaml` runs:

```text
S3 originals -> convert/upload PNGs -> checksum audit -> SAM3 reads S3
-> register in FiftyOne -> approval -> checkpoint cleanup
```

Conversion and the checksum audit use the CPU image. The audit re-downloads and
verifies all indexed original and prepared objects before pre-labeling; a
failure prevents pre-labeling and registration. The audit retries twice on
failure and starts its checks from the beginning on each attempt. Pre-labeling
requests one NVIDIA GPU, uses the existing per-node training mutex, and retries
failed attempts using completed image checkpoints.
Conversion, audit and pre-labeling receive the storage Secret; registration
receives the FiftyOne database Secret.

Use the existing `nachet-training-workspace-pvc` in `argo-workflows`. Each run
writes COCO files under `/workspace/<workflow-name>/` and downloads the model to
`/workspace/<workflow-name>/models/sam3_hf_transformers`. Automatic retries
reuse that run's completed model download and compatible image checkpoints.
Pre-label checkpoints from the previous PVC-mounted model use a different model
identity and are regenerated. Checkpoint cleanup leaves the downloaded model
in the run directory.

Howard's `nachet-preparation-config` ConfigMap sets the cold Ceph endpoint,
the `nachet-seed-image-dataset` bucket, the region and FiftyOne's media root.
The `model-bucket` key supplies `MODEL_BUCKET` for
`s3://${MODEL_BUCKET}/base/sam3_hf_transformers`.
The `nachet-preparation-cold-s3` Secret provides `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY`, with `AWS_SESSION_TOKEN` for temporary credentials.
The credentials need `s3:ListBucket` for the model prefix and `s3:GetObject`
for the snapshot files.
The workflow explicitly passes `--allow-http` for Howard's internal Ceph
connection. HTTPS connections still verify certificates and use `AWS_CA_BUNDLE`
when configured.

Howard also supplies `nachet-preparation-fiftyone` with `FIFTYONE_DATABASE_URI`.
The server media root must map the COCO image keys to paths FiftyOne can read.
Confirm the mount, available workspace capacity and model-bucket access before
running. Apply the updated WorkflowTemplate and select a SAM3 image built from
the same revision before submitting.

```bash
argo submit -n argo-workflows --from workflowtemplate/nachet-preparation \
  -p code-revision="$CODE_REVISION" -p dataset-name=collection-01-review \
  -p raw-prefix=raw/collection-01 \
  -p model-revision="$MODEL_REVISION"
```

For the temporary duplicate-conflict bypass, append
`-p duplicate-conflicts=warn`. The workflow defaults to `error`, just like the
CLIs. Before using the new parameter, rebuild and select the updated CPU image
and apply the updated
[`preparation-workflow-template.yaml`](../workflows/preparation-workflow-template.yaml).
An existing image or running container does not acquire the new CLI option
automatically.

To skip invalid images with warnings and index records, append
`-p invalid-images=skip`; the workflow defaults to strict `error`.
Argo assigns the workflow name at submission. Copy it from the `Name` shown by
`argo submit` or from the workflow list in the Argo UI. The preparation steps
use that name to locate checkpoints and COCO files on the workspace.

To reuse checkpoints in a new submission, pass
`-p resume-run-id=<previous-workflow-name>` with the name of the latest attempt
that owns the checkpoints. The source run must be idle during the handoff.
The new run copies the checkpoints to staging, verifies their SHA-256
checksums, and publishes the verified copy under its own workflow name.
If there are checkpoint files to remove, Argo pauses at
`approve-previous-checkpoint-cleanup`. Once other users of the source
checkpoints have finished, resume that step to clean up the source checkpoints
and continue. Cleanup rechecks both copies before deleting source files. Allow
enough free workspace storage for both copies until the handoff completes.

`prepare-images` and `prelabel` update the new run's local checkpoints. If that
run is interrupted after the handoff, use its workflow name for the next
resume. The default `resume-run-id` is the current workflow name for a fresh
run. Keep the same conversion and model settings and immutable collection.
The full workflow still runs the prepared-image checksum audit. Build and
select the updated CPU image and deploy the WorkflowTemplate before using the
handoff.

To audit an earlier prepared index, select `audit-checksums` as the entrypoint
and set `index-run-id` to the workflow that completed `prepare-images` and
wrote `index.coco.json`. The `index-run-id` field appears for direct audit and
pre-label entrypoints and defaults to `resume-run-id`.
For example, if run B resumed from A and then finished `prepare-images`,
both the completed index and the latest checkpoints are under B.
The report is written under the new workflow's directory and does not replace
the earlier report. The index must already exist: preparation writes it only
after all non-skipped images have completed. A direct audit runs no later
steps. Rebuild and select the updated CPU image and apply the updated
WorkflowTemplate; older images do not support `--report-path`.

To resume only pre-labeling, set `CHECKPOINT_RUN` to the workflow that owns the
prediction checkpoints and `INDEX_RUN` to the workflow that completed
`prepare-images`. Select the `prelabel` entrypoint:

```bash
argo submit -n argo-workflows --from workflowtemplate/nachet-preparation \
  --entrypoint prelabel -p resume-run-id="$CHECKPOINT_RUN" -p index-run-id="$INDEX_RUN" \
  -p code-revision="$CODE_REVISION" -p model-revision="$MODEL_REVISION" \
  -p raw-prefix=raw/collection-01 -p dataset-name=collection-01-review
```

The index is read from
`/workspace/<index-workflow-name>/prepared/index.coco.json`; the draft is
written under the new workflow's directory. To start fresh predictions against
an existing index, pass only `index-run-id` and leave `resume-run-id` at its
default. A resume with prediction checkpoints uses the same copy and
approval flow as the full workflow. First verify that the previous audit passed for
that exact index and bucket, and that the index, originals and prepared PNGs
have not changed since. The report does not bind itself to the index hash, and
the pre-label step does not verify the report.

If the index and prediction checkpoints are in the same run, omit
`index-run-id` to use its default. Use the same model folder and revision to
reuse prediction checkpoints. In the full workflow, pre-labeling always uses
the current run's freshly audited index.

To start only registration from an existing draft, set `DRAFT_RUN` to the name
of the workflow that wrote it and select the `register-for-review` entrypoint:

```bash
argo submit -n argo-workflows --from workflowtemplate/nachet-preparation \
  --entrypoint register-for-review -p draft-run-id="$DRAFT_RUN" \
  -p dataset-name=collection-01-review -p raw-prefix=raw/collection-01 \
  -p code-revision="$CODE_REVISION" -p model-revision="$MODEL_REVISION"
```

The draft is read from
`/workspace/<draft-workflow-name>/prepared/draft.coco.json`. For a direct
pre-labeling run, use that new workflow's name, not necessarily the earlier
checkpoint or index workflow. `draft-run-id` defaults to `resume-run-id`. The
full workflow always registers its own draft regardless of this input.

This entrypoint does not run preparation, audit, pre-labeling or cleanup.
Registration starts a new import rather than resuming individual samples and
still refuses an existing dataset name. A killed import can leave a temporary
dataset, as described above under "Register for review".

After registration, the full workflow separately suspends at
`approve-current-checkpoint-cleanup` to authorize cleanup of its own
checkpoints. Both approvals apply only to checkpoint files in the selected
run. COCO files and audit reports remain available for direct steps.

To clean an earlier run, including a failed run, submit the separate cleanup
workflow and resume its approval step only when all dependent runs are finished:

```bash
argo submit -n argo-workflows --from workflowtemplate/nachet-preparation-cleanup \
  -p run-name=<earlier-workflow-name>
```

Cleanup removes recognized legacy and versioned checkpoint files
only. Unexpected files or symlinks cause cleanup to fail rather than removing
unrecognized data.

The images default to the `main` tags, as in the training workflows, and the
workspace defaults to `nachet-training-workspace-pvc`. Override the image
references with digests to pin them. The supplied image uses `Sam3Predictor`.
The preparation function already accepts an injected predictor; another
architecture needs its own adapter and runtime dependencies. The code and model
revisions are operator-supplied labels; they are not checked against the image
or weights.

Registration creates the dataset for human review; reviewed export, release
publication and training use their own components. FiftyOne stores the source
records in MongoDB; ownership of the controller mappings remains open.

## Checks

```bash
uv sync --project mlops/preparation --locked --group storage
uv run --project mlops/preparation --no-sync python -m pytest mlops/preparation/tests
```

The SDK tests use FiftyOne 1.22.1 and a disposable MongoDB. They cover registration,
interrupted imports and the workflow's command arguments, using the shared
storage provider with a fake S3 SDK and supplied predictions. The workflow test
checks source paths, hashes, boxes and splits through the preparation steps and
retries.

```bash
uv sync --project mlops/preparation --locked --group fiftyone --group storage
PREPARATION_TEST_MONGO_URI='<disposable-mongo-uri>' \
  uv run --project mlops/preparation --no-sync python -m pytest \
  mlops/preparation/integration_tests -q
```

The deployed FiftyOne media mount and live S3 still need checking.

## Research origins

Adapted from `ai-cfia/nachet-model-ccds`:

- Image conversion: `nachetmodel/tiff_jpg_to_png.py` at `b7ba50b`.
- COCO indexing: `notebooks/1.01_js_init_coco_dataset.ipynb` at `52988ae`.
- SAM3 drafts: `notebooks/1.02_js_pre_annotate_sam3_hf.ipynb` at `b7ba50b`.

Copyright (c) 2025 AI @ Canadian Food Inspection Agency (CFIA).
See the [MIT licence](../../LICENSE).

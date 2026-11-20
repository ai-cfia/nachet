# MLOps

The standalone [dataset release tools](datasets/README.md) publish reviewed
COCO versions, generate seed crops and provide verified training inputs. Their
storage adapter, registry migration, dependencies and tests live in `datasets/`.

The [dataset release Argo workflows](datasets/README.md#argo-release-and-smoke-workflows)
publish and validate a prepared release, or run a small integration smoke test
against a separately provisioned test registry and object store. Their templates
are included in `workflows/kustomization.yaml` alongside the training workflows.

## Train from a reviewed release

Prepare the FiftyOne COCO export against the existing PNGs, then publish a
ready release. Enable crop generation before publishing a release for both
trainers. Hand off the publication's dataset name, version, manifest SHA-256,
and S3 bucket. [Reviewed-data handoff in #968](https://github.com/ai-cfia/nachet/issues/968)

Submit `nachet-detector-training` and `nachet-classifier-training` with the same
`dataset-name`, `dataset-version`, and `expected-manifest-sha256` parameters.
Set `dataset-container` if the bucket differs from `DATASET_CONTAINER` in the
release credentials Secret. Use the default `smoke` profile for a small release.

Both workflows use the `nachet-training-dataset-release` Secret by default.
Set `dataset-credentials-secret` to use another Secret. The Secret needs
`DATASET_DATABASE_URL`, `DATASET_REGISTRY_SCHEMA` for a non-default PostgreSQL
schema, and S3 read credentials. For Ceph, use the dataset-specific
`S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY` settings. Grant read
access to the release registry and the bucket's release objects. Training uses
its existing PVC for base model weights, checkpoints, and optional external
evaluation inputs.

A CPU pod verifies the ready release, manifest pin, and object checksums before
the workflow schedules a GPU pod. RT-DETR reads the reviewed detection PNGs and
boxes. Swin reads the published crops and their labels. Both use the declared
train and validation splits, reserve the test split, and assign class indices
by sorted reviewed COCO category ID. Training streams verified media by batch
from S3 without a local image cache. The parent MLflow runs and training attempts
record `dataset_name`, `dataset_version`, and `dataset_manifest_sha256`.

Leave the release parameters empty to use the existing PVC dataset inputs.

## Example approval workflow

`workflows/example-workflow-template.yaml` is a small control-flow example used
to verify Nachet's Argo Workflows setup before model-training steps are added.
It accepts a `dataset-name` parameter and runs three steps:

1. `validate-input` checks the dataset name and publishes it as an output.
2. `await-approval` pauses the workflow.
3. `record-approval` consumes the validated output after the workflow resumes.

The example does not process a dataset or train a model. It checks that a
parameter reaches the run, that one step can pass an output to another, and
that the run can stop for review before it continues.

## Deployment

The template is deployed from Git. Howard's `nachet-mlops` Argo CD application
watches the `mlops/workflows` directory on Nachet's `main` branch and
synchronizes its rendered resources to the `argo-workflows` namespace.
Kustomize packages the tested `scripts/record-stage.sh` file into a ConfigMap
that the example mounts read-only. The ConfigMap keeps a stable name because the
`WorkflowTemplate` refers to that name directly.

Merging a change updates the template in Howard; it does not start a workflow
run. Do not apply the template manually in Howard because Argo CD owns the
deployed copy.

For local testing outside Howard, apply it with:

```bash
kubectl apply --kustomize mlops/workflows
```

Run the script checks independently with:

```bash
mlops/workflows/tests/record-stage-test.sh
```

## Run the workflow

In the Argo Workflows UI:

1. Open **Workflow Templates**.
2. Select `nachet-workflow-control-example`.
3. Submit the template, using either the default dataset name or a test value.
4. Wait for the run to stop at `await-approval`.
5. Review the completed step, then select **Resume** to continue.

For this example, resuming the workflow means approving it. Terminate the run
if it should not continue. There is no separate approve/reject record yet.

The same workflow can be submitted from the command line:

```bash
argo submit \
  --namespace argo-workflows \
  --from workflowtemplate/nachet-workflow-control-example \
  --parameter dataset-name=my-dataset
```

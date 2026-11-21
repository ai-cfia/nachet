# MLOps

The standalone [dataset release tools](datasets/README.md) publish reviewed
COCO versions, generate seed crops and provide verified training inputs. Their
storage adapter, registry migration, dependencies and tests live in `datasets/`.

The [dataset release Argo workflows](datasets/README.md#argo-release-and-smoke-workflows)
publish and validate a prepared release, or run a small integration smoke test
against a separately provisioned test registry and object store. Their templates
are included in `workflows/kustomization.yaml` alongside the training workflows.

## Training checkpoints

Both trainers save full resume checkpoints to the shared training PVC each
epoch and upload them through the existing MLflow integration. The full
profile keeps the two most recent checkpoints locally; the smoke profile keeps
one. `checkpoint-retention` can override this count.

The review dropdown includes successfully archived checkpoints from that
workflow's MLflow attempts, even after local rotation removes them. Selecting
an older checkpoint downloads it before evaluation. Resume and standalone
export can restore missing checkpoints too. Keep the run's `mlflow-run-id`
file so those operations can find its archives. Failed uploads are excluded
from the archive list, and failed downloads do not create selectable local
checkpoint directories. Existing local checkpoints remain usable.

To restore one checkpoint explicitly with the trainer runtime:

```bash
python -m checkpoints --runs-root /runs --run-id <training-workflow> \
  restore --checkpoint checkpoint-<step>
```

Saving stays enabled because training needs model weights, optimizer,
scheduler and RNG state to resume. RAM-backed storage would lose its contents
with the pod. Leave room for another checkpoint while it is being saved and
for any older checkpoints selected for review. This retention limit applies
to each training run, not the entire PVC: retained runs, restored candidates,
dataset inputs, base models and exports still need a storage budget.

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

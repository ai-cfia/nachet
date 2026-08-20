# Example approval workflow

`example-workflow-template.yaml` is a small workflow used to verify Nachet's
Argo Workflows setup before model-training steps are added. It accepts a
`dataset-name` parameter and runs three steps:

1. `prepare` prints the supplied dataset name.
2. `await-approval` pauses the workflow.
3. `complete` runs after the workflow is resumed.

The example does not process a dataset or train a model. It checks that a
parameter reaches the run and that the run can stop for review before it
continues.

## Deployment

The template is deployed from Git. Howard's `nachet-mlops` Argo CD application
watches this directory on Nachet's `main` branch and synchronizes its YAML files
to the `argo-workflows` namespace.

Merging a change updates the template in Howard; it does not start a workflow
run. Do not apply the template manually in Howard because Argo CD owns the
deployed copy.

For local testing outside Howard, apply it with:

```bash
kubectl apply --filename mlops/example-workflow-template.yaml
```

## Run the workflow

In the Argo Workflows UI:

1. Open **Workflow Templates**.
2. Select `nachet-mlops-example`.
3. Submit the template, using either the default dataset name or a test value.
4. Wait for the run to stop at `await-approval`.
5. Review the completed step, then select **Resume** to continue.

For this example, resuming the workflow means approving it. Terminate the run
if it should not continue. There is no separate approve/reject record yet.

The same workflow can be submitted from the command line:

```bash
argo submit \
  --namespace argo-workflows \
  --from workflowtemplate/nachet-mlops-example \
  --parameter dataset-name=my-dataset
```

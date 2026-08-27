# Nachet MLOps workflows

This directory contains the Argo `WorkflowTemplate` resources maintained with
Nachet. Howard deploys them to the cluster; merging a template does not start a
workflow run.

The Argo controller, UI, and Nachet workflows run in `argo-workflows`.

## Control-flow example

`workflows/example-workflow-template.yaml` is a small deployment check. It:

1. validates a `dataset-name` input;
2. passes the validated value to the next step;
3. pauses for a manual decision;
4. records the approval after the run resumes.

It does not process data or train a model.

To run it in the Argo UI:

1. Open **Workflow Templates**.
2. Select `nachet-workflow-control-example`.
3. Choose **Submit** and enter a dataset name.
4. Wait for `await-approval` to pause.
5. Open the paused node and resume it.

The same template can be submitted from the command line:

```bash
argo submit \
  --namespace argo-workflows \
  --from workflowtemplate/nachet-workflow-control-example \
  --parameter dataset-name=my-dataset
```

## Deployment

Howard's `nachet-mlops` Argo CD application watches `mlops/workflows` on
Nachet's `main` branch. Argo CD renders the Kustomization and synchronizes the
result into `argo-workflows`.

For local testing, apply the same Kustomization to a test cluster:

```bash
kubectl apply --kustomize mlops/workflows
```

Run the example's script test separately:

```bash
mlops/workflows/tests/record-stage-test.sh
```

The detector training workflow has its own setup and operating notes in
[`training/README.md`](training/README.md).

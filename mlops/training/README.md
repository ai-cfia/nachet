# Detector training with Argo Workflows

`nachet-detector-training` runs the existing RT-DETR training code through
Argo. It supports a short smoke run and the reviewed 101-species configuration.

## Before running it

The matching Howard configuration must be deployed first. It gives the Argo
controller access to the managed `ailab-shared` namespace and creates the
`nachet-workflow` service account used by Nachet templates.

The namespace also needs:

- the existing `ailab-shared-pvc` and `ghcr-image-pull-secret`;
- a small `detector-smoke-v1` dataset for the first cluster run;
- a reviewed `101-species-v1` snapshot before a full run;
- a writable `nachet/detector-training/runs` directory on the shared volume;
- the `nachet-training-s3` External Secret for MLflow artifact storage.

The workflow does not create missing datasets, credentials, or directories.
It stops when a required input is unavailable.

The shared volume must have this shape:

```text
/ailab/nachet/detector-training/
  inputs/
    detector-smoke-v1/
      data/
      models/rtdetr_v2_r50vd/
      notebooks/shell/training_config_smoke.yaml
    101-species-v1/
      data/
      models/rtdetr_v2_r50vd/
      notebooks/shell/training_config_101spp_all.yaml
  runs/
```

Paths inside each dataset configuration are relative to that dataset profile.
Absolute paths and paths that leave the selected profile are rejected.

The profile is one reviewed input unit. Its YAML selects the COCO and image
sources and contains the `include_classes` list; its `reject_list.txt` files
exclude individual images. These files stay beside the prepared data rather
than being copied into the container or fetched from another Git repository at
runtime. Before training, the wrapper verifies the paths and confirms that
every included class appears in at least one source's COCO category table. It
records the source matches, hashes, and counts in the run receipt. The trainer
also stores the dataset configuration with the MLflow run, and the wrapper
stores the small reject lists beside it. Images and COCO files remain in the
reviewed snapshot; their paths and COCO hashes are recorded without duplicating
the dataset.

## Start a run

Open **Workflow Templates** in Argo and select `nachet-detector-training`.
The main inputs are:

- `dataset-profile`: the prepared dataset snapshot;
- `run-profile`: `smoke` or `full`;
- `gpu-profile`: `ai-lab-1`, `ai-lab-2`, or `ai-lab-3`.

AI Lab 1 is the default. The workflow uses a mutex for each physical GPU so two
Nachet training jobs do not intentionally share the same device.

The remaining training fields use `profile-default` unless someone needs a
reviewed override. The full profile keeps the June 2026 settings: 50 epochs,
640-pixel inputs, batch size 24, one gradient-accumulation step, 760 warm-up
steps, learning rate `0.00001`, and seed `2438`.

Submit the template after reviewing the inputs. A new run leaves
`resume-run-id` as `none` and `resume-checkpoint` as `latest`.

## What the workflow does

The run follows this sequence:

```text
validate request
-> train on the selected GPU
-> list the completed checkpoints
-> pause for checkpoint selection
-> validate the selected checkpoint
```

The training step writes its request, logs, result, MLflow identifiers, and
checkpoints below `/runs/<workflow-name>`. It checks that Kubernetes
scheduled the pod on the requested node and that exactly one CUDA device is
visible.

The wrapper opens one MLflow run before training starts. The migrated trainer
logs its metrics and parameters to that run. Transformers' MLflow callback also
logs each checkpoint when the trainer saves it. After training, the workflow
lists only local `checkpoint-<step>` directories that contain the model,
optimizer, scheduler, random state, training arguments, and Trainer state
needed for a resume. It does not upload them a second time. The shared-volume
copy is retained so a failed run can still resume while the storage and
retention policy is being established.

The workflow exposes these outputs:

- MLflow run ID;
- MLflow run URL;
- the generated checkpoint options;
- the selected checkpoint.

## Select a checkpoint

Checkpoint selection happens inside the same workflow run:

1. Wait for the `review-checkpoints` node to show **Suspended**.
2. Open the MLflow URL in the workflow outputs and compare the completed
   checkpoints.
3. Select the suspended node in Argo.
4. Choose one checkpoint from the generated dropdown.
5. Resume that node.

Do not use the workflow-level Resume button for this step. The node-level
button opens Argo's intermediate-parameter form. The next step verifies that
the chosen name belongs to the set produced by this run.

The workflow ends after recording the selection. Evaluating that checkpoint on
the independent dataset is a separate pipeline stage.

The dropdown uses Argo's documented [intermediate parameters][argo-inputs]
format. The listing step emits `{"enum": [...]}`, which Argo renders as a
choice list when the suspend node is reached.

## Resume failed training

Argo preserves the failed workflow record, but the trainer needs a checkpoint
to continue its model state. Start a new workflow and set:

- `resume-run-id` to the failed workflow name;
- `resume-checkpoint` to `latest` or a specific `checkpoint-<step>`.

The wrapper reuses the earlier MLflow run and passes the checkpoint path to
Hugging Face's `resume_from_checkpoint` argument. The local checkpoint
directories remain available so the run is recoverable.

## Source and runtime

The detector code came from `ai-cfia/nachet-model-ccds` commit
`601219b7c9fcfc68f2ec51293edbab8cf3e0bc3a`.

- `detector/src/coco_to_hf_dataset.py` came from
  `nachetmodel/coco_to_hf_dataset.py`. Only the provenance header changed.
- `detector/src/train_detector.py` came from
  `nachetmodel/HFTrainer_detector_2026061501_js.py`. Only the provenance header
  and filename changed.

The wrapper passes `report_to=mlflow` and enables Transformers'
`HF_MLFLOW_LOG_ARTIFACTS` setting. This makes the existing trainer callback log
each saved checkpoint to the run that the wrapper opened. Tests pin the
migrated source hashes so an unreviewed change cannot silently drift from this
baseline.

The image starts from NVIDIA's `25.10` PyTorch image, pinned by digest. This is
the same public base used by the repository's tracked GPU development
environment. The detector requirements are pinned separately, including the
exact Transformers commit used by the migrated trainer. The image then adds
the reviewed scripts and a non-root entry point.

Version `0.1.0` is the first testable runtime. The publish workflow refuses to
overwrite an existing version tag. Increment `VERSION` whenever the runtime
changes after publication. The cluster smoke run remains necessary because a
successful image build cannot prove compatibility with the cluster's GPUs,
mounted data, MLflow service, or Ceph object store.

## Development checks

Run the unit tests:

```bash
python3 -m unittest discover -s mlops/training/detector/tests -v
```

Lint and render the workflow:

```bash
argo lint --offline mlops/workflows/detector-training-workflow-template.yaml
kubectl kustomize mlops/workflows
```

These checks do not replace the cluster smoke run. The smoke run must still
prove image pulling, CephFS access, MLflow and S3 connectivity, GPU scheduling,
and the training code together.

[argo-inputs]: https://argo-workflows.readthedocs.io/en/release-4.0/intermediate-inputs/

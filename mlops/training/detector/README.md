# Detector training runtime

This directory builds the detector training image. It is a standalone uv
project, like `backend/`; it is not a shared environment for all training jobs.

## Dependencies

`pyproject.toml` declares the Python dependencies and `uv.lock` records their
resolved versions. Generate the lockfile with uv; do not edit it by hand.

Training requires the NVIDIA PyTorch image pinned in the Dockerfile. The
project's virtual environment can access the base image's system packages,
including CUDA-enabled PyTorch. uv excludes `torch` from dependency resolution
so it does not install a replacement. The base image and lockfile together
define the environment; `uv sync` alone on a laptop is not a complete training
setup.

## Build and check

Run these commands from this directory:

```bash
docker build --platform linux/amd64 -t nachet-detector-trainer:local .
docker run --rm --platform linux/amd64 --network none \
  nachet-detector-trainer:local --help
```

The build checks that `uv.lock` is current and that the training libraries
import without replacing NVIDIA's CUDA-enabled PyTorch. Actual GPU training
still requires a compatible NVIDIA host, prepared inputs and MLflow configuration.

The build also runs all tests in `tests/`, with networking disabled. A failed
test stops the build. Test files are mounted for that step, not copied into
the image.

All detector tests live in `tests/`. The evaluation regression tests need
PyTorch and the project dependencies; they use a small model with random
weights and run on CPU. Run the full suite in the built image as its non-root
user:

```bash
docker run --rm --platform linux/amd64 --network none \
  --mount "type=bind,src=$(pwd)/tests,dst=/opt/nachet-detector/tests,readonly" \
  --entrypoint python nachet-detector-trainer:local \
  -m unittest discover -s /opt/nachet-detector/tests -p 'test_*.py' -v
```

These tests do not validate GPU execution, cluster storage or live MLflow.

## Update dependencies or the version

Use Python 3.12 and the uv version pinned in the Dockerfile. After changing
dependencies in `pyproject.toml`, regenerate and check the lockfile:

```bash
uv lock
uv lock --check
```

To bump the trainer version, update `[project].version` in `pyproject.toml`
and run `uv lock` again. Review and commit both files together,
then rebuild the image to check compatibility with the NVIDIA packages.

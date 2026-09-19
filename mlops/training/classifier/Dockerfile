FROM nvcr.io/nvidia/pytorch:25.10-py3@sha256:42263b2424fc237b34c4fc4a91c30d603c57eed36e37d31ff6d9a4f1f801edee

# Use the same uv version that generates and validates the project lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /usr/local/bin/

USER root
WORKDIR /opt/nachet-classifier

COPY classifier/pyproject.toml classifier/uv.lock ./

# Keep NVIDIA's PyTorch visible while installing the locked project dependencies
# into a separate environment. Syncing must not replace the base image's torch.
RUN uv venv --system-site-packages .venv \
    && uv lock --check \
    && uv sync --frozen --no-dev --no-cache

ENV PATH="/opt/nachet-classifier/.venv/bin:$PATH"

COPY classifier/src ./src
COPY checkpoints.py training_runtime.py training_options.py /opt/

# Fail the build if project dependencies shadow NVIDIA's CUDA-enabled PyTorch.
RUN python -c "\
import accelerate, boto3, datasets, mlflow, sklearn; \
import torch, torchvision, transformers; \
from pathlib import Path; import sys; \
assert not Path(torch.__file__).is_relative_to(sys.prefix), 'Expected NVIDIA base-image PyTorch'; \
assert torch.version.cuda, 'Expected CUDA-enabled PyTorch'"

ENV HOME=/tmp \
    PYTHONPATH=/opt/nachet-classifier/src:/opt \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

# Exercise training on a tiny local model without a GPU, network or MLflow server.
RUN --mount=type=bind,source=classifier/tests,target=/opt/nachet-classifier/tests \
    --network=none \
    HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
    python -m unittest discover -s tests -p 'test_*.py' -v

ENTRYPOINT ["python", "/opt/nachet-classifier/src/run_training.py"]

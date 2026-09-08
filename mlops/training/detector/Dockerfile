FROM nvcr.io/nvidia/pytorch:25.10-py3@sha256:42263b2424fc237b34c4fc4a91c30d603c57eed36e37d31ff6d9a4f1f801edee

# Use the same uv version that generates and validates the project lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /usr/local/bin/

USER root
WORKDIR /opt/nachet-detector

# OpenCV's native libraries depend on libxcb even when using the headless wheel.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock VERSION ./

# The published image tag comes from VERSION; it must match the Python project.
RUN if [ "$(uv version --short)" != "$(cat VERSION)" ]; then \
        echo "VERSION must match the version in pyproject.toml" >&2; \
        exit 1; \
    fi

# Keep NVIDIA's PyTorch visible while installing the locked project dependencies
# into a separate environment. Syncing must not replace the base image's torch.
RUN uv venv --system-site-packages .venv \
    && uv lock --check \
    && uv sync --frozen --no-dev --no-cache

ENV PATH="/opt/nachet-detector/.venv/bin:$PATH"

COPY src ./src

# Fail the build if project dependencies shadow NVIDIA's CUDA-enabled PyTorch.
RUN python -c "\
import accelerate, albumentations, boto3, cv2, datasets, mlflow; \
import pycocotools, torch, torchmetrics, torchvision, transformers; \
from pathlib import Path; import sys; \
assert not Path(torch.__file__).is_relative_to(sys.prefix), 'Expected NVIDIA base-image PyTorch'; \
assert torch.version.cuda, 'Expected CUDA-enabled PyTorch'"

RUN chown -R 10001:10001 /opt/nachet-detector

ENV HOME=/tmp \
    PYTHONPATH=/opt/nachet-detector/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

ENTRYPOINT ["python", "/opt/nachet-detector/src/run_training.py"]

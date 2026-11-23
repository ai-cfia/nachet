FROM nvcr.io/nvidia/pytorch:25.10-py3@sha256:42263b2424fc237b34c4fc4a91c30d603c57eed36e37d31ff6d9a4f1f801edee

# Use the same uv version that generates and validates the project lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /usr/local/bin/

USER root
WORKDIR /opt/mlops/training/classifier

# The release reader imports OpenCV, which needs libxcb.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY blob /opt/mlops/blob
COPY datasets/pyproject.toml /opt/mlops/datasets/
COPY datasets/dataset_release /opt/mlops/datasets/dataset_release
COPY datasets/utility /opt/mlops/datasets/utility
COPY training/classifier/pyproject.toml training/classifier/uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/nachet-classifier/.venv

# Keep NVIDIA's PyTorch visible while installing the locked project dependencies
# into a separate environment. Syncing must not replace the base image's torch.
RUN uv venv --system-site-packages "$UV_PROJECT_ENVIRONMENT" \
    && uv lock --check \
    && uv sync --frozen --no-dev --group test --no-cache

ENV PATH="/opt/nachet-classifier/.venv/bin:$PATH" \
    ORT_DISABLE_TELEMETRY=1

WORKDIR /opt/nachet-classifier
COPY training/classifier/src ./src
COPY training/*.py /opt/

# Keep NVIDIA's PyTorch and require the GPU-enabled ONNX Runtime build.
RUN python -c "\
import dataset_release.reader; import accelerate, boto3, datasets, mlflow, sklearn; \
import torch, torchvision, transformers; import onnxruntime as ort; \
from pathlib import Path; import sys; \
assert not Path(torch.__file__).is_relative_to(sys.prefix), 'Expected NVIDIA base-image PyTorch'; \
assert torch.version.cuda, 'Expected CUDA-enabled PyTorch'; \
assert 'CUDAExecutionProvider' in ort.get_available_providers(), 'Expected CUDA-enabled ONNX Runtime'"

ENV HOME=/tmp \
    LOGURU_LEVEL=WARNING \
    PYTHONPATH=/opt/nachet-classifier/src:/opt \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

# Exercise training on a tiny local model without a GPU, network or MLflow server.
RUN --mount=type=bind,source=training/classifier/tests,target=/opt/nachet-classifier/tests \
    --network=none \
    HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
    python -m unittest discover -s tests -p 'test_*.py' -v

ENTRYPOINT ["python", "/opt/nachet-classifier/src/run_training.py"]

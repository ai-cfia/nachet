FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.24@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /usr/local/bin/uv

WORKDIR /opt/preparation
# OpenCV needs libxcb1 even in the headless conversion image.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# The shared project stays beside preparation, as in the repository.
COPY blob /opt/blob
COPY preparation/pyproject.toml preparation/uv.lock ./
ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1

FROM base AS checks
RUN uv sync --locked --group storage --no-cache
COPY preparation/*.py ./
RUN --mount=type=bind,source=preparation/tests,target=/opt/preparation/tests \
    --network=none \
    uv run --no-sync python -m pytest tests -q

FROM base AS cpu
RUN uv sync --locked --no-dev --group storage --no-cache
ENV PATH="/opt/preparation/.venv/bin:$PATH" \
    PYTHONPATH=/opt/preparation
COPY --from=checks /opt/preparation/prepare_images.py /opt/preparation/prepare_s3.py /opt/preparation/s3_storage.py ./
USER 10001:10001
ENTRYPOINT ["python"]

FROM cpu AS sam3
USER root
RUN uv sync --locked --no-dev --group storage --group sam3 --no-cache
COPY preparation/prelabel.py ./
# PyPI supplies CUDA-enabled torch on linux/amd64. This is an import check,
# not evidence that the cluster GPU/driver can run SAM3.
RUN python -c "import torch, torchvision; from transformers import Sam3Model, Sam3Processor; assert torch.version.cuda, 'Expected CUDA-enabled PyTorch'"
USER 10001:10001

FROM cpu AS registration
USER root
RUN uv sync --locked --no-dev --group storage --group fiftyone --no-cache
COPY preparation/register_fiftyone.py ./
ENV FIFTYONE_DO_NOT_TRACK=true
RUN python -c "from importlib.metadata import version; assert version('fiftyone') == '1.22.1'" \
    && python register_fiftyone.py --help
USER 10001:10001

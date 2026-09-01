FROM nvcr.io/nvidia/pytorch:25.10-py3@sha256:42263b2424fc237b34c4fc4a91c30d603c57eed36e37d31ff6d9a4f1f801edee

USER root
WORKDIR /opt/nachet-detector

# OpenCV's native libraries depend on libxcb even when using the headless wheel.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install alongside the CUDA-enabled PyTorch provided by the NVIDIA base image.
RUN uv pip install --system --break-system-packages --no-cache -r requirements.txt

COPY src ./src

RUN python -c \
    "import accelerate, albumentations, boto3, cv2, datasets, mlflow, pycocotools, torch, torchmetrics, transformers"

RUN chown -R 10001:10001 /opt/nachet-detector

ENV HOME=/tmp \
    PYTHONPATH=/opt/nachet-detector/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

ENTRYPOINT ["python", "/opt/nachet-detector/src/run_training.py"]

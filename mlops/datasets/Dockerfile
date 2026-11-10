FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.24@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /usr/local/bin/uv

WORKDIR /opt/datasets
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# The build context is mlops so the locked sibling package stays beside datasets.
COPY blob /opt/blob
COPY datasets/pyproject.toml datasets/uv.lock ./
COPY datasets/dataset_release ./dataset_release
COPY datasets/utility ./utility
COPY workflows/scripts/dataset_release_smoke.py /opt/workflows/scripts/dataset_release_smoke.py
ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS checks
RUN uv sync --locked --no-cache
RUN --mount=type=bind,source=datasets/tests,target=/opt/datasets/tests \
    --mount=type=bind,source=datasets/migrations,target=/opt/datasets/migrations \
    --mount=type=bind,source=datasets/alembic.ini,target=/opt/datasets/alembic.ini \
    --mount=type=bind,source=test_support,target=/opt/test_support \
    --mount=type=bind,source=workflows/tests,target=/opt/workflows/tests \
    --network=none \
    uv run --no-sync python -I -m pytest -c pyproject.toml \
      tests ../workflows/tests/test_dataset_release_smoke.py -q

FROM base AS runtime
RUN uv sync --locked --no-dev --no-cache
ENV PATH="/opt/datasets/.venv/bin:$PATH"
COPY --from=checks /opt/workflows/scripts/dataset_release_smoke.py /opt/workflows/scripts/dataset_release_smoke.py
USER 10001:10001
ENTRYPOINT ["python", "-m", "dataset_release"]

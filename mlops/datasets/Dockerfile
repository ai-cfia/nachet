FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.24@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /usr/local/bin/uv

WORKDIR /opt/mlops/datasets
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# The build context is mlops so the locked sibling package stays beside datasets.
COPY blob /opt/mlops/blob
COPY datasets/pyproject.toml datasets/uv.lock ./
COPY datasets/dataset_release ./dataset_release
COPY datasets/utility ./utility
COPY workflows/scripts/dataset_release_smoke.py /opt/workflows/scripts/dataset_release_smoke.py
ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS checks
RUN uv sync --locked --no-cache
# Test sources are temporary bind mounts, not files stored in image layers.
RUN --mount=type=bind,source=datasets/tests,target=/opt/mlops/datasets/tests \
    --mount=type=bind,source=datasets/migrations,target=/opt/mlops/datasets/migrations \
    --mount=type=bind,source=datasets/alembic.ini,target=/opt/mlops/datasets/alembic.ini \
    --mount=type=bind,source=workflows/tests,target=/opt/workflows/tests \
    --network=none \
    uv run --no-sync python -I -m pytest -c pyproject.toml \
      tests /opt/workflows/tests/test_dataset_release_smoke.py -q

# Start from base so the runtime excludes the checks stage's test dependencies.
FROM base AS runtime
RUN uv sync --locked --no-dev --no-cache
ENV PATH="/opt/mlops/datasets/.venv/bin:$PATH"
# Require successful checks while copying only the runtime smoke helper.
COPY --from=checks /opt/workflows/scripts/dataset_release_smoke.py /opt/workflows/scripts/dataset_release_smoke.py
USER 10001:10001
ENTRYPOINT ["python", "-m", "dataset_release"]

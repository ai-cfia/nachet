FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS dependencies

COPY --from=ghcr.io/astral-sh/uv:0.11.24@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /usr/local/bin/uv
WORKDIR /opt/nachet-export
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
ARG UV_OFFLINE=false
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=nachet-export-uv,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --no-install-project \
    && uv pip check

FROM dependencies AS test-dependencies
RUN --mount=type=cache,id=nachet-export-uv,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --group test --no-install-project \
    && uv pip check

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS scripts
WORKDIR /opt/nachet-export
COPY export_model.py browser_cam.py ./mlops/export/
RUN ln -s mlops/export/export_model.py export_model.py \
    && ln -s mlops/export/browser_cam.py browser_cam.py
ENV PATH="/opt/nachet-export/.venv/bin:$PATH" \
    HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HOME=/tmp/huggingface TORCH_HOME=/tmp/torch \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
USER 10001:10001

FROM scripts AS runtime
COPY --from=dependencies /opt/nachet-export/.venv ./.venv
ENTRYPOINT ["python", "/opt/nachet-export/export_model.py"]

FROM scripts AS test
COPY --from=test-dependencies /opt/nachet-export/.venv ./.venv
COPY tests ./mlops/export/tests
ENTRYPOINT ["python", "-m", "pytest", "/opt/nachet-export/mlops/export/tests", "-p", "no:cacheprovider"]
CMD ["-q"]

FROM runtime AS final

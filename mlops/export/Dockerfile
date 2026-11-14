FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9

# Use the same uv version that generates and validates the project lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.11.24@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /uvx /usr/local/bin/

WORKDIR /opt/nachet-export

COPY pyproject.toml uv.lock ./
RUN uv lock --check \
    && uv sync --frozen --no-dev --no-cache

ENV PATH="/opt/nachet-export/.venv/bin:$PATH"

COPY export_model.py browser_cam.py ModelRelease.py ./

ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

# Test the runtime without keeping test files in the image.
RUN --mount=type=bind,source=tests,target=/opt/nachet-export/tests \
    --network=none \
    python -m unittest discover -s tests -p 'test_*.py' -v

ENTRYPOINT ["python"]

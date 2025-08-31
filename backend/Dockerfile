FROM python:3.11-bullseye

WORKDIR /app

ENV QUART_APP=app.py
ENV QUART_ENV=development
ENV PYTHONUNBUFFERED True
ENV PYTHONPATH=/app

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies using uv
COPY pyproject.toml uv.lock LICENSE README.md ./

RUN uv sync --frozen

CMD hypercorn -b :$BACKEND_DEV_PORT app:app

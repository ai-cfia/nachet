FROM python:3.13-bullseye

WORKDIR /app

ENV QUART_APP=app.py
ENV QUART_ENV=development
ENV PYTHONUNBUFFERED True
ENV PYTHONPATH=/app

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies using uv
COPY . ./

RUN uv sync --frozen

CMD ["sh", "-c", "uv run hypercorn -b :$BACKEND_DEV_PORT app/main:app"]

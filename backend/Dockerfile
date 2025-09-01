FROM python:3.11-bullseye

WORKDIR /app

ENV QUART_APP=app.py
ENV QUART_ENV=development
ENV PYTHONUNBUFFERED True
ENV PYTHONPATH=/app

# Install uv
RUN pip install --no-cache-dir uv

COPY ./pyproject.toml ./uv.lock ./LICENSE ./README.md ./

# Install dependencies using uv
RUN uv sync --frozen

COPY . ./

CMD hypercorn -b :$PORT app:app

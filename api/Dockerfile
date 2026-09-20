# syntax=docker/dockerfile:1
# Copyright 2026 Aaron John Schlosser, PhD.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ARG GIT_COMMIT=
RUN --mount=type=bind,from=gitmeta,target=/tmp/git \
    printf '%s' "${GIT_COMMIT:-$(git --git-dir=/tmp/git rev-parse --short HEAD 2>/dev/null || true)}" > /app/git-commit \
    && chmod 644 /app/git-commit \
    && apt-get purge -y git \
    && apt-get autoremove -y

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

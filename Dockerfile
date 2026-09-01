FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/data/huggingface \
    NLTK_DATA=/data/nltk_data \
    TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3.12 -m venv "$VIRTUAL_ENV"

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    dl_translate \
    cupy-cuda12x \
    nltk \
    pydantic \
    fast_langdetect \
    langchain_chroma \
    langchain_ollama \
    langchain_core \
    keybert \
    "redis[hiredis]>=5.0.0" \
    sentence_transformers \
    "spacy[cuda12x]" \
    textblob \
    "en_core_web_lg @ https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl" \
    "fr_core_news_lg @ https://github.com/explosion/spacy-models/releases/download/fr_core_news_lg-3.8.0/fr_core_news_lg-3.8.0-py3-none-any.whl"

COPY api/ /app/src/

WORKDIR /app/src

EXPOSE 8081

CMD ["python", "main.py"]
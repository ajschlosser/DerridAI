# Copyright 2026 Aaron John Schlosser, PhD

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""models.py -- Convenience wrappers for Ollama models.

The module exports two helper functions:

* :func:`get_embeddings` -- returns an :class:`OllamaEmbeddings` instance
  configured with the default settings from :mod:`config`.
* :func:`get_llm_chat` -- returns a :class:`ChatOllama` instance for local
  LLM inference.

Logging is performed via :func:`src.derrida.logging.get_logger` so that all
model-related messages share a consistent format.
"""

from langchain_ollama import ChatOllama, OllamaEmbeddings
from config import (
    CHAT_TEMPERATURE,
    OLLAMA_SERVER_URL,
    EMBEDDING_MODEL,
    CHAT_MODEL,
)
from helpers import get_logger

LOG = get_logger(__name__)


def get_embeddings() -> OllamaEmbeddings:
    """Create and return an embedding model.

    The model is configured to stay resident in memory (`keep_alive="-1"`)
    to avoid the overhead of cold‑starts during batch indexing.
    """
    LOG.info("Loading embedding model %s.", EMBEDDING_MODEL)
    return OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_SERVER_URL,
        keep_alive="-1"
    )


def get_llm_chat() -> ChatOllama:
    """Create and return a chat model for local inference.

    The returned :class:`ChatOllama` instance uses the global temperature
    setting from :mod:`config`.
    """
    LOG.info("Initializing local LLM '%s'.", CHAT_MODEL)
    return ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_SERVER_URL,
        temperature=CHAT_TEMPERATURE,
        timeout=45.0,  # e.g., 45 s
    )
    
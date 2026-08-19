# src/derrida/config/__init__.py

"""
Configuration package for the DerridAI RAG project.

Provides the default constants from :mod:`.defaults` and an optional
environment‑variable override mechanism.
"""

import os
from . import defaults
from .defaults import args

# -- Optional: Override with environment variables ---------------------------------
# For each constant, if an env var of the same name exists, use it.
# This keeps the defaults file clean while allowing runtime overrides.

def _env_override(name: str, default):
    """Return the env var if set, otherwise the provided default."""
    v = os.getenv(name)
    if v is not None:
        return v
    elif args.__dict__.get(name.lower()) is not None:
        return args.__dict__[name.lower()]
    return default

EMBEDDING_MODEL   = _env_override("EMBEDDING_MODEL", defaults.EMBEDDING_MODEL)
CHAT_MODEL        = _env_override("CHAT_MODEL", defaults.CHAT_MODEL)
CHAT_TEMPERATURE  = float(_env_override("CHAT_TEMPERATURE", defaults.CHAT_TEMPERATURE))
OLLAMA_SERVER_URL = _env_override("OLLAMA_SERVER_URL", defaults.OLLAMA_SERVER_URL)

DB_PATH          = _env_override("DB_PATH", defaults.DB_PATH)
SOURCE_TEXT      = _env_override("SOURCE_TEXT", defaults.SOURCE_TEXT)

BATCH_SIZE       = int(_env_override("BATCH_SIZE", defaults.BATCH_SIZE))
K_VALUE          = int(_env_override("K_VALUE", defaults.K_VALUE))
FETCH_K_VALUE    = int(_env_override("FETCH_K_VALUE", defaults.FETCH_K_VALUE))
LAMBDA_MULT_VALUE = float(_env_override("LAMBDA_MULT_VALUE", defaults.LAMBDA_MULT_VALUE))

# Re‑export so ``from src.derrida.config import EMBEDDING_MODEL`` works
__all__ = [
    "EMBEDDING_MODEL",
    "CHAT_MODEL",
    "CHAT_TEMPERATURE",
    "OLLAMA_SERVER_URL",
    "DB_PATH",
    "SOURCE_TEXT",
    "BATCH_SIZE",
    "K_VALUE",
    "FETCH_K_VALUE",
    "LAMBDA_MULT_VALUE",
    "args"
]

# -- Helper to get the current configuration as a dict -------------------------
def get_config_dict() -> dict:
    """Return the current configuration values as a plain dictionary."""
    return {
        "EMBEDDING_MODEL": EMBEDDING_MODEL,
        "CHAT_MODEL": CHAT_MODEL,
        "CHAT_TEMPERATURE": CHAT_TEMPERATURE,
        "OLLAMA_SERVER_URL": OLLAMA_SERVER_URL,
        "DB_PATH": DB_PATH,
        "SOURCE_TEXT": SOURCE_TEXT,
        "BATCH_SIZE": BATCH_SIZE,
        "K_VALUE": K_VALUE,
        "FETCH_K_VALUE": FETCH_K_VALUE,
        "LAMBDA_MULT_VALUE": LAMBDA_MULT_VALUE,
    }
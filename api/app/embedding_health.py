# Copyright 2026 Aaron John Schlosser, PhD.
"""Reachability check for the configured embedding provider and model.

Everything that builds a derived vector projection (metadata exemplars, validated
claim memory, vector stores) resolves its embedder from the same Settings default
(Vector stores and retrieval → Vector database defaults). This performs one real,
tiny embedding call with that configuration and explains a failure in terms the
administrator can act on.
"""

from __future__ import annotations

import time
from typing import Any

PROBE_TEXT = "DerridAI embedding probe"


def _hint(provider: str, model: str | None, error: Exception, base_url: str) -> str:
    text = f"{type(error).__name__}: {error}".casefold()
    if provider == "precomputed":
        return (
            "Precomputed vectors cannot embed query text, so semantic retrieval "
            "(metadata examples, validated-claim memory) cannot use this default. "
            "Choose Ollama, Chroma, or a provider profile."
        )
    if "not found" in text and ("model" in text or "pull" in text) or "404" in text:
        return (
            f"The server answered but does not have the model {model!r}. "
            f"For Ollama, run `ollama pull {model}` on that host."
        )
    if any(marker in text for marker in ("name or service not known", "connecterror", "connection refused", "timed out", "nodename")):
        where = f" at {base_url}" if base_url else ""
        return (
            f"The embedding server{where} could not be reached. From inside Docker, "
            "`localhost` is the container itself; use the host's address (for example "
            "http://host.docker.internal:11434)."
        )
    if "401" in text or "403" in text or "api key" in text:
        return "The provider rejected the credentials; check the API key on the provider profile."
    if provider == "chroma":
        return (
            "Chroma's built-in embedder downloads its model on first use, which fails "
            "without network access. Use Ollama or a provider profile for offline use."
        )
    return ""


def _resolved_base_url(provider: str) -> str:
    from .config import settings
    from .system_store import system_store

    if provider == "ollama":
        return str(settings.ollama_base_url)
    if provider.startswith("profile:"):
        profile = system_store.researcher_profile(provider.split(":", 1)[1].strip()) or {}
        return str(profile.get("base_url") or "")
    return ""


def check_embedding_defaults(
    provider: str | None = None,
    model: str | None = None,
    *,
    embedder: Any | None = None,
) -> dict[str, Any]:
    """Embed one short string with the saved (or supplied) defaults and report the outcome."""
    from .chroma_store import Embeddings
    from .system_store import system_store

    saved = system_store.embedding_defaults()
    chosen_provider = str(provider or saved.get("embedding_provider") or "").strip()
    if not chosen_provider.startswith("profile:"):
        chosen_provider = chosen_provider.lower()
    chosen_model = (model if provider else saved.get("embedding_model")) or None
    chosen_model = str(chosen_model).strip() if chosen_model else None
    result: dict[str, Any] = {
        "provider": chosen_provider, "model": chosen_model, "reachable": False,
        "dimension": None, "latency_ms": None, "error": "", "hint": "",
    }
    embedder = embedder or Embeddings()
    started = time.monotonic()
    try:
        vector = embedder.embed_query(PROBE_TEXT, provider=chosen_provider, model=chosen_model)
        result.update(reachable=True, dimension=len(vector), latency_ms=int((time.monotonic() - started) * 1000))
    except Exception as exc:
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        result["error"] = f"{type(exc).__name__}: {exc}"[:400]
        try:
            base_url = _resolved_base_url(chosen_provider)
        except Exception:
            base_url = ""
        result["hint"] = _hint(chosen_provider, chosen_model, exc, base_url)
    return result

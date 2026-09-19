"""Robust LLM translation of interface dictionaries (release 0.35.17, "Lingua Franca").

Why: administrators can machine-translate the UI into new languages. Local models
often return broken JSON or wrap it in an extra key, so the pipeline must repair,
split (bisect) and finally fall back to plain text rather than fail the language.
How: stubs the app.rag module (avoids real LLM/Chroma dependencies), re-imports
app.i18n_translation, and replaces chat_complete with fake providers.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
TRANSLATION = (ROOT / "api/app/i18n_translation.py").read_text(encoding="utf-8")












def test_translation_pipeline_has_json_repair_bisection_and_plain_text_last_resort(monkeypatch):
    """Invalid JSON for large batches is recovered by splitting and, if needed, plain text.

    Contract checks (source text): batch limits (24 items / 6,500 chars) and the repair,
    bisect and plain-text helpers still exist.
    Behavior: a fake provider returns "not json" for batches larger than 3 items and
    valid JSON otherwise, so 12 strings must be bisected. Expected: all 12 translated,
    zero failures, and more than one structured call.
    """
    assert "max_items: int = 24" in TRANSLATION
    assert "max_chars: int = 6_500" in TRANSLATION
    assert "_extract_translation_json" in TRANSLATION
    assert "translate_single_plain" in TRANSLATION
    assert "Bisect it and retry" in TRANSLATION

    rag_stub = ModuleType("app.rag")
    rag_stub._extract_json = lambda raw: json.loads(raw)
    rag_stub.chat_complete = lambda **kwargs: "{}"
    monkeypatch.setitem(sys.modules, "app.rag", rag_stub)
    sys.modules.pop("app.i18n_translation", None)
    module = importlib.import_module("app.i18n_translation")

    source = {f"ui.item_{i}": f"Save interface setting number {i}" for i in range(12)}
    calls = {"structured": 0, "plain": 0}

    def brittle_chat(**kwargs):
        if kwargs.get("json_mode") is False:
            calls["plain"] += 1
            original = kwargs["prompt"].rsplit("\n\n", 1)[-1]
            return "ES " + original
        calls["structured"] += 1
        # Simulate a provider that emits invalid structured output for larger
        # requests but succeeds after the pipeline splits them.
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        if len(batch) > 3:
            return "not json"
        return json.dumps({key: f"ES {value}" for key, value in batch.items()})

    monkeypatch.setattr(module, "chat_complete", brittle_chat)
    translated, stats = module.translate_english_dictionary(
        code="es-MX", dictionary=source, provider="ollama", model="translator", base_url=None, api_key=None
    )
    assert len(translated) == len(source)
    assert stats["failed_count"] == 0
    assert calls["structured"] > 1


def test_translation_pipeline_accepts_common_nested_translation_wrapper(monkeypatch):
    """Accept {"translations": {...}} as well as a flat mapping.

    Why: models commonly wrap the answer in a "translations" object; rejecting it would
    discard a correct translation. Expect both strings translated with no failures.
    """
    rag_stub = ModuleType("app.rag")
    rag_stub._extract_json = lambda raw: json.loads(raw)
    rag_stub.chat_complete = lambda **kwargs: "{}"
    monkeypatch.setitem(sys.modules, "app.rag", rag_stub)
    sys.modules.pop("app.i18n_translation", None)
    module = importlib.import_module("app.i18n_translation")

    source = {"action.save": "Save changes", "action.cancel": "Cancel changes"}

    def wrapped_chat(**kwargs):
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        return json.dumps({"translations": {key: f"FR {value}" for key, value in batch.items()}})

    monkeypatch.setattr(module, "chat_complete", wrapped_chat)
    translated, stats = module.translate_english_dictionary(
        code="fr-FR", dictionary=source, provider="ollama", model="translator", base_url=None, api_key=None
    )
    assert translated == {key: f"FR {value}" for key, value in source.items()}
    assert stats["failed_count"] == 0


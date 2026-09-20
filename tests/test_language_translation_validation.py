"""LLM dictionary translation validation and locale codes.

Why: machine-translated UI text must keep every {placeholder} and must be a real
translation. Locale codes must be normalized to BCP 47 and right-to-left scripts
must set the document direction.
How: stubs app.rag so the translation module imports without an LLM, then swaps in
fake chat functions that return good, damaged, or untranslated output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
I18N_STORE = (ROOT / "web/src/stores/i18n.ts").read_text(encoding="utf-8")








def test_translation_helper_accepts_valid_output_and_rejects_bad_provider_output(monkeypatch):
    """Accept a faithful translation; reject dropped placeholders and untranslated output.

    1) Valid: 3 strings translate in one batch and "{count}" survives.
    2) Damaged: "ui.count" is returned as "Hallo" without {count}, which must raise
       LanguageTranslationError mentioning "placeholder".
    3) Echo: a model that returns the English unchanged for 25 strings must raise
       "did not produce a usable" translation.
    Why: shipping broken placeholders crashes screens; shipping English as "German" is a
    silent failure.
    """
    import importlib
    import sys
    from types import ModuleType

    rag_stub = ModuleType("app.rag")
    rag_stub._extract_json = lambda raw: json.loads(raw)
    rag_stub.chat_complete = lambda **kwargs: "{}"
    monkeypatch.setitem(sys.modules, "app.rag", rag_stub)
    sys.modules.pop("app.i18n_translation", None)
    module = importlib.import_module("app.i18n_translation")

    source = {
        "ui.hello": "Hello world",
        "ui.count": "Found {count} records",
        "ui.save": "Save changes",
    }

    def valid_chat(**kwargs):
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        return json.dumps({key: f"DE {value}" for key, value in batch.items()}, ensure_ascii=False)

    monkeypatch.setattr(module, "chat_complete", valid_chat)
    translated, stats = module.translate_english_dictionary(
        code="de-DE",
        dictionary=source,
        provider="ollama",
        model="translator",
        base_url=None,
        api_key=None,
    )
    assert set(translated) == set(source)
    assert translated["ui.count"].endswith("{count} records")
    assert stats["key_count"] == 3
    assert stats["batch_count"] == 1

    def damaged_chat(**kwargs):
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        return json.dumps({key: ("Hallo" if key == "ui.count" else value) for key, value in batch.items()})

    monkeypatch.setattr(module, "chat_complete", damaged_chat)
    with pytest.raises(module.LanguageTranslationError, match="placeholder"):
        module.translate_english_dictionary(
            code="de-DE",
            dictionary=source,
            provider="ollama",
            model="translator",
            base_url=None,
            api_key=None,
        )

    many = {f"ui.item_{i}": f"This is interface sentence number {i}" for i in range(25)}
    def untranslated_chat(**kwargs):
        return kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1]

    monkeypatch.setattr(module, "chat_complete", untranslated_chat)
    with pytest.raises(module.LanguageTranslationError, match="did not produce a usable"):
        module.translate_english_dictionary(
            code="es-MX",
            dictionary=many,
            provider="ollama",
            model="not-a-translator",
            base_url=None,
            api_key=None,
        )


def test_bcp47_normalization_and_rtl_document_direction():
    """Locale codes are normalized, and RTL scripts set the page direction.

    Normalization: "pt_br" -> "pt-BR", "zh-hant-tw" -> "zh-Hant-TW". Frontend wiring is
    checked in the i18n store source (directionForLocale, document dir, Arabic and
    Hebrew script codes); this part is a text-presence check, not a browser test.
    """
    from app.system_store import normalize_locale_code

    assert normalize_locale_code("de") == "de"
    assert normalize_locale_code("pt_br") == "pt-BR"
    assert normalize_locale_code("zh-hant-tw") == "zh-Hant-TW"
    assert "directionForLocale" in I18N_STORE
    assert "document.documentElement.dir = directionForLocale" in I18N_STORE
    assert '"Arab"' in I18N_STORE and '"Hebr"' in I18N_STORE





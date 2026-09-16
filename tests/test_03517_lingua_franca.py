from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/legacy/runtime.js").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
SYSTEM = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
LANGUAGES = (ROOT / "web/src/views/LanguagesView.vue").read_text(encoding="utf-8")
FLAG_PICKER = (ROOT / "web/src/components/CountryFlagPicker.vue").read_text(encoding="utf-8")
READING = (ROOT / "web/src/components/record/RecordReadingPane.vue").read_text(encoding="utf-8")
FAQ = (ROOT / "web/src/views/ResponseFaqView.vue").read_text(encoding="utf-8")
REPORT = (ROOT / "web/src/components/research/EvaluationReport.vue").read_text(encoding="utf-8")
TRANSLATION = (ROOT / "api/app/i18n_translation.py").read_text(encoding="utf-8")
HTTP = (ROOT / "web/src/api/http.ts").read_text(encoding="utf-8")


def test_release_identity_and_notes():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.37.1"
    assert 'version="0.37.1"' in MAIN
    assert '"app_version": "0.37.1"' in MAIN
    assert "DerridAI 0.37.1" in (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
    assert "0.35.17 — Lingua Franca" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_research_payload_is_normalized_before_post_and_400_is_not_used_for_rag_start():
    assert 'reranker=["cross_encoder","lexical","none"].includes' in RUNTIME
    assert 'responseLanguage=["auto","en","fr"].includes' in RUNTIME
    assert "The selected corpus database is no longer available" in RUNTIME
    assert "selected.length>500" in RUNTIME
    assert "selectedPayload.length!==selected.length" in RUNTIME
    assert "unsupported provider" in RUNTIME
    endpoint = MAIN[MAIN.index('@app.post("/api/jobs/rag")'):MAIN.index('@app.post("/api/jobs/upsert")')]
    assert "status_code=400" not in endpoint
    assert "status_code=422" in endpoint
    assert "status_code=500" in endpoint


def test_http_errors_keep_full_status_message_and_response_body():
    for source in (RUNTIME, HTTP):
        assert "derridai.httpErrors.v1" in source
        assert "responseBody" in source
        assert "statusText" in source
        assert "fullMessage" in source
    assert "rows.slice(0,50)" in RUNTIME
    assert "rows.slice(0, 50)" in HTTP


def test_annotation_escape_and_accessible_hover_focus_tooltip():
    assert "window.addEventListener('keydown',onGlobalKeydown)" in READING
    assert "if(selectedQuote.value)" in READING
    assert "record-annotation-tooltip" in READING
    assert 'role="tooltip"' in READING
    assert "@mouseenter=\"showAnnotationTooltip" in READING
    assert "@focus=\"showAnnotationTooltip" in READING
    assert "annotation.tags" in READING and "annotation.author" in READING and "created_at" in READING


def test_built_in_language_names_are_region_neutral_but_flags_are_locale_specific():
    assert '"en-US": {"name": "English", "flag": "🇺🇸"' in SYSTEM
    assert '"fr-CA": {"name": "Français", "flag": "🇨🇦"' in SYSTEM
    assert '"language.english_us": "English"' in SYSTEM
    assert '"language.french_ca": "Français"' in SYSTEM
    assert 'name: "English", flag: "🇺🇸"' in (ROOT / "web/src/stores/i18n.ts").read_text(encoding="utf-8")
    assert 'name: "Français", flag: "🇨🇦"' in (ROOT / "web/src/stores/i18n.ts").read_text(encoding="utf-8")
    assert 'i18n.t("language.english_us", "English")' in LANGUAGES


def test_flag_picker_teleports_outside_modal_and_explains_quebec_symbol():
    assert '<teleport to="body">' in FLAG_PICKER
    assert "position:fixed" in FLAG_PICKER
    assert "updatePopoverPosition" in FLAG_PICKER
    assert 'const QUEBEC_SYMBOL = "⚜️"' in FLAG_PICKER
    assert "Unicode defines no standardized Québec flag emoji" in FLAG_PICKER
    assert "language.quebec_symbol_help" in FLAG_PICKER
    assert (ROOT / "web/src/components/CountryFlagPicker.stories.ts").exists()


def test_translation_pipeline_has_json_repair_bisection_and_plain_text_last_resort(monkeypatch):
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

def test_response_faq_uses_structured_evaluation_report_with_raw_output_secondary():
    assert "EvaluationReport" in FAQ
    assert ':report="entry.result||entry"' in FAQ
    assert "evaluation-categories" in REPORT
    assert "unsupported_or_risky_claims" in REPORT
    assert "Technical raw output" in REPORT
    assert 'role="meter"' in REPORT
    assert (ROOT / "web/src/components/research/EvaluationReport.stories.ts").exists()

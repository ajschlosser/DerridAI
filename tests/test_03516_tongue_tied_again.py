from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_VIEW = (ROOT / "web/src/views/LanguagesView.vue").read_text(encoding="utf-8")
JOBS = (ROOT / "api/app/jobs.py").read_text(encoding="utf-8")
MODELS = (ROOT / "api/app/models.py").read_text(encoding="utf-8")
RUNTIME = (ROOT / "web/src/legacy/runtime.js").read_text(encoding="utf-8")
RESEARCH = (ROOT / "web/src/views/ResearchView.vue").read_text(encoding="utf-8")
LLM_TOOLS = (ROOT / "api/app/llm_tools.py").read_text(encoding="utf-8")
SYSTEM = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")


def test_03516_release_identity():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    main = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
    assert package["version"] == "0.42.1"
    assert 'version="0.42.1"' in main
    assert '"app_version": "0.42.1"' in main
    assert "Corpus Viewer 0.42.1" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "DerridAI 0.42.1" in (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
    assert "0.35.16 — Tongue Tied Again" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_language_table_identity_warning_and_resume_ui():
    assert ".language-string-head{position:static" in LANGUAGE_VIEW
    assert "align-items:start" in LANGUAGE_VIEW
    assert "modelTranslationRisk" in LANGUAGE_VIEW
    assert "language.model_translation_risk_ack" in LANGUAGE_VIEW
    assert "resumableInstallJob" in LANGUAGE_VIEW
    assert "openResumeDialog" in LANGUAGE_VIEW
    assert "language.translation_incomplete_title" in LANGUAGE_VIEW
    assert "trackedFallbackKeys" in LANGUAGE_VIEW
    assert "language.needs_review" in LANGUAGE_VIEW
    assert "resume_job_id" in LANGUAGE_VIEW
    assert "resume_job_id" in MODELS


def test_translation_tolerates_under_ten_percent_and_retains_partial_for_larger_failure(monkeypatch):
    rag_stub = ModuleType("app.rag")
    rag_stub._extract_json = lambda raw: json.loads(raw)
    rag_stub.chat_complete = lambda **kwargs: "{}"
    monkeypatch.setitem(sys.modules, "app.rag", rag_stub)
    sys.modules.pop("app.i18n_translation", None)
    module = importlib.import_module("app.i18n_translation")

    source = {f"ui.item_{i}": f"Interface sentence number {i}" for i in range(20)}

    def one_missing(**kwargs):
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        return json.dumps({key: f"DE {value}" for key, value in batch.items() if key != "ui.item_3"})

    monkeypatch.setattr(module, "chat_complete", one_missing)
    translated, stats = module.translate_english_dictionary(
        code="de-DE", dictionary=source, provider="ollama", model="translator", base_url=None, api_key=None
    )
    assert stats["failed_count"] == 1
    assert stats["fallback_count"] == 1
    assert stats["failed_keys"] == ["ui.item_3"]
    assert translated["ui.item_3"] == source["ui.item_3"]
    assert translated["ui.item_4"].startswith("DE ")

    ten = {f"ui.ten_{i}": f"Another interface sentence {i}" for i in range(10)}

    def ten_percent_missing(**kwargs):
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        return json.dumps({key: f"FR {value}" for key, value in batch.items() if key != "ui.ten_0"})

    monkeypatch.setattr(module, "chat_complete", ten_percent_missing)
    with pytest.raises(module.LanguageTranslationError) as caught:
        module.translate_english_dictionary(
            code="fr-FR", dictionary=ten, provider="ollama", model="translator", base_url=None, api_key=None
        )
    assert caught.value.failed_keys == ["ui.ten_0"]
    assert len(caught.value.partial_dictionary) == 9
    assert "failed (10%" in str(caught.value)


def test_translation_resume_skips_validated_strings(monkeypatch):
    rag_stub = ModuleType("app.rag")
    rag_stub._extract_json = lambda raw: json.loads(raw)
    rag_stub.chat_complete = lambda **kwargs: "{}"
    monkeypatch.setitem(sys.modules, "app.rag", rag_stub)
    sys.modules.pop("app.i18n_translation", None)
    module = importlib.import_module("app.i18n_translation")

    source = {f"ui.item_{i}": f"Interface sentence number {i}" for i in range(12)}
    partial = {key: f"ES {value}" for key, value in source.items() if key not in {"ui.item_2", "ui.item_7"}}
    seen: list[set[str]] = []

    def translate_pending(**kwargs):
        batch = json.loads(kwargs["prompt"].split("SOURCE (en-US):\n", 1)[1])
        seen.append(set(batch))
        return json.dumps({key: f"ES {value}" for key, value in batch.items()})

    monkeypatch.setattr(module, "chat_complete", translate_pending)
    translated, stats = module.translate_english_dictionary(
        code="es-MX",
        dictionary=source,
        provider="ollama",
        model="translator",
        base_url=None,
        api_key=None,
        resume_dictionary=partial,
        retry_keys=["ui.item_2", "ui.item_7"],
    )
    assert seen == [{"ui.item_2", "ui.item_7"}]
    assert stats["resumed_count"] == 10
    assert stats["failed_count"] == 0
    assert len(translated) == len(source)


def test_partial_dictionary_stays_server_side_and_translation_report_is_durable():
    assert 'current["_resume_dictionary"]' in JOBS
    assert 'current["_resume_failed_keys"]' in JOBS
    assert 'not str(key).startswith("_")' in JOBS
    # The resumable payload sent to the browser contains counts/samples, not the whole dictionary.
    public_block = JOBS[JOBS.index("public_stats = {"):JOBS.index("raise", JOBS.index("public_stats = {"))]
    assert '"partial_dictionary"' not in public_block
    assert "translation_report=translation_report" in JOBS
    assert "translation_report: dict[str, Any] | None" in SYSTEM
    assert 'report["failed_keys"] = unresolved' in SYSTEM


def test_research_empty_database_enters_creation_workflow_and_preserves_shell_navigation():
    assert "if(!(snapshot.stores||[]).length){" in RESEARCH
    assert "runtime.openDatabaseCreationFromResearch?.()" in RESEARCH
    assert 'await router.replace(canOpenDatabase?"/databases":"/")' not in RESEARCH
    assert "function openDatabaseCreationFromResearch()" in RUNTIME
    assert "state.vectorAutoCreateRequested=true" in RUNTIME
    assert 'detail:{path:"/databases",legacyView:"vector"}' in RUNTIME
    assert "if(noCollections&&state.vectorAutoCreateRequested)" in RUNTIME
    assert "window.setTimeout(openCreateWizard,0)" in RUNTIME


def test_rag_grades_preserve_full_structured_output():
    assert 'normalized["categories"] = categories' in LLM_TOOLS
    assert 'normalized["analysis"]' in LLM_TOOLS
    assert 'normalized["raw_output"] = original' in LLM_TOOLS
    assert "Each category must contain an integer `score`" in LLM_TOOLS
    assert "max_tokens=4096" in LLM_TOOLS

    if str(ROOT / "api") not in sys.path:
        sys.path.insert(0, str(ROOT / "api"))
    module = importlib.import_module("app.llm_tools")
    raw = {
        "categories": {
            "query_relevance": {"score": 9, "analysis": "Directly answers the question."},
            "source_binding": {"score": 8, "analysis": "Most claims are source-bound."},
        },
        "overall": {"score": 8, "analysis": "Strong with one traceability gap."},
        "analysis": "Full grader reasoning retained.",
        "summary": "Strong answer.",
        "strengths": ["Good attribution"],
    }
    normalized = module._normalize_rag_grade_payload(raw)
    assert normalized["query_relevance"] == 9
    assert normalized["overall"] == 8
    assert normalized["categories"]["query_relevance"]["analysis"] == "Directly answers the question."
    assert normalized["categories"]["overall"]["analysis"] == "Strong with one traceability gap."
    assert normalized["analysis"] == "Full grader reasoning retained."
    assert normalized["raw_output"] == raw

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_VIEW = (ROOT / "web/src/views/LanguagesView.vue").read_text(encoding="utf-8")
COUNTRY_PICKER = (ROOT / "web/src/components/CountryFlagPicker.vue").read_text(encoding="utf-8")
LANGUAGE_HEADER = (ROOT / "web/src/components/LanguageWorkspaceHeader.vue").read_text(encoding="utf-8")
I18N_STORE = (ROOT / "web/src/stores/i18n.ts").read_text(encoding="utf-8")
APP = (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
JOBS = (ROOT / "api/app/jobs.py").read_text(encoding="utf-8")
TRANSLATION = (ROOT / "api/app/i18n_translation.py").read_text(encoding="utf-8")
SYSTEM = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")


def test_03512_release_version_is_consistent():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.40.20"
    assert 'version="0.40.20"' in MAIN
    assert '"app_version": "0.40.20"' in MAIN
    assert "Corpus Viewer 0.40.20" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "DerridAI 0.40.20" in APP
    assert "0.35.12 — Tongue Twister" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_languages_page_is_a_bilingual_localization_studio():
    assert "LanguageWorkspaceHeader" in LANGUAGE_VIEW
    assert "CountryFlagPicker" in LANGUAGE_VIEW
    assert 'language.english_source' in LANGUAGE_VIEW
    assert "sourceValue(key)" in LANGUAGE_VIEW
    assert 'statusFilter' in LANGUAGE_VIEW
    assert 'language.matches_english' in LANGUAGE_VIEW
    assert 'language.search_strings' in LANGUAGE_VIEW
    assert 'language.search_locales' in LANGUAGE_VIEW
    assert ':dir="i18n.directionForLocale(current.code)"' in LANGUAGE_VIEW
    assert 'language.atomic_install' in LANGUAGE_VIEW
    assert 'language.translation_failed_detail' in LANGUAGE_VIEW


def test_country_flag_library_and_storybook_coverage_exist():
    codes = re.search(r"const COUNTRY_CODES = \[(.*?)\] as const;", COUNTRY_PICKER, re.S)
    assert codes is not None
    assert len(re.findall(r"'[A-Z]{2}'", codes.group(1))) >= 249
    assert "Intl.DisplayNames" in COUNTRY_PICKER
    assert "Intl.Locale" in COUNTRY_PICKER
    assert 'role="group"' in COUNTRY_PICKER
    assert 'aria-pressed' in COUNTRY_PICKER
    assert (ROOT / "web/src/components/CountryFlagPicker.stories.ts").exists()
    assert (ROOT / "web/src/components/LanguageWorkspaceHeader.stories.ts").exists()
    assert "localization_summary" in LANGUAGE_HEADER


def test_install_translation_is_bounded_validated_and_atomic():
    assert "_chunk_dictionary" in TRANSLATION
    assert "max_items: int = 24" in TRANSLATION
    assert "max_chars: int = 6_500" in TRANSLATION
    assert "placeholder(s) changed" in TRANSLATION
    assert "effectively untranslated" in TRANSLATION or "did not produce a usable" in TRANSLATION
    assert "translate_english_dictionary(" in JOBS
    assert "translate_english_dictionary(" in MAIN
    language_runner = JOBS[JOBS.index("def _run_language_dictionary"):JOBS.index("def _run(", JOBS.index("def _run_language_dictionary"))]
    assert language_runner.index("translate_english_dictionary(") < language_runner.index("system_store.put_language(")
    assert '"dictionary": clean' not in language_runner


def test_translation_helper_accepts_valid_output_and_rejects_bad_provider_output(monkeypatch):
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
    from app.system_store import normalize_locale_code

    assert normalize_locale_code("de") == "de"
    assert normalize_locale_code("pt_br") == "pt-BR"
    assert normalize_locale_code("zh-hant-tw") == "zh-Hant-TW"
    assert "directionForLocale" in I18N_STORE
    assert "document.documentElement.dir = directionForLocale" in I18N_STORE
    assert '"Arab"' in I18N_STORE and '"Hebr"' in I18N_STORE


def test_provider_navigation_warns_and_native_back_path_survives_legacy_destination():
    assert "manageProvidersConfirm" in LANGUAGE_VIEW
    assert "Leave language installation?" in LANGUAGE_VIEW
    assert 'detail: { path: "/providers", legacyView: "providers" }' in LANGUAGE_VIEW
    assert "function navigateNative(path:string,legacyView?:string)" in APP
    assert "nativeBackPath.value=current" in APP
    assert "runtime.navigateView(legacyView,path)" in APP
    assert "detail.legacyView" in APP


def test_language_dialogs_have_focus_management_and_escape_support():
    assert "trapFocus" in LANGUAGE_VIEW
    assert "restoreConfirmationFocus" in LANGUAGE_VIEW
    assert "focusDialog" in LANGUAGE_VIEW
    assert '@keydown.esc.stop.prevent="manageProvidersConfirm=false"' in LANGUAGE_VIEW
    assert '@keydown.esc.stop.prevent="pendingLocaleCode=\'\'"' in LANGUAGE_VIEW
    assert '@keydown.esc.stop.prevent="pendingDelete=null"' in LANGUAGE_VIEW
    assert COUNTRY_PICKER.count("min-height:44px") >= 1

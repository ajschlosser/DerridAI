from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
SEARCH = (ROOT / "web/src/views/SearchView.vue").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
SYSTEM = ((ROOT / "api/app/system_store.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")

def test_release_version_and_name():
    package=json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.50.0"
    assert 'version="0.50.0"' in (ROOT / "api/app/main.py").read_text(encoding="utf-8")
    assert "# DerridAI Corpus Viewer 0.50.0" in README
    assert "0.36.11 — Peekaboo" in README

def test_loaded_search_has_fixed_requested_columns_and_no_column_button():
    assert 'const SEARCH_LOADED_COLUMNS=["__db_status","work","page_start","needs_review","text"]' in RUNTIME
    assert 'const columns=scope==="loaded"' in RUNTIME
    assert "v-if=\"databaseMode&&snapshot.layout!=='cards'\"" in SEARCH
    assert 'v-if="databaseMode" type="button" class="search-column-resizer"' in SEARCH

def test_citation_menu_is_overlay_popover():
    assert '.record-citation-popover{position:absolute' in STYLE
    assert 'z-index:80' in STYLE

def test_works_add_jsonl_cta_and_response_library_rename():
    assert 'id="worksAddJsonl"' in RUNTIME
    assert 'document.querySelector("#fileInput")?.click()' in RUNTIME
    assert "'nav.faq': 'Response Library'" in SYSTEM
    assert "'nav.faq': 'Bibliothèque de réponses'" in SYSTEM
    assert 'The New England Transcendental Club of California' in (ROOT / "web/src/App.vue").read_text(encoding="utf-8")

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
SYSTEM = ((ROOT / "api/app/system_store.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8"))
INSPECTOR = (ROOT / "web/src/components/record/RecordInspector.vue").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")


def test_0364_release_identity():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.53.0"
    assert 'version="0.53.0"' in MAIN
    assert '"app_version": "0.53.0"' in MAIN
    assert "# DerridAI Corpus Viewer 0.53.0" in README
    assert "0.36.4 — Oops You Did It Again" in README


def test_export_overwrite_ux_is_removed():
    assert "showSaveFilePicker" not in RUNTIME
    assert "showDirectoryPicker" not in RUNTIME
    assert "exportOverwrite" not in RUNTIME
    assert "function doExport(kind)" in RUNTIME
    assert 'data-export="current"' in RUNTIME


def test_record_inspector_page_is_inline_below_region_author():
    assert "'region_type','region_author','__pages','primary_text'" in INSPECTOR
    assert "key==='__pages'" in INSPECTOR
    assert "record-page-context" not in INSPECTOR


def test_work_insights_use_targets_and_role_share_not_speaker_position_holder():
    block = RUNTIME[RUNTIME.index("function workInsightMetrics"):RUNTIME.index("function workInsightPieHtml")]
    assert 'field:"target"' in block
    assert 'field:"discourse_role"' in block
    assert 'type:"pie"' in block
    assert 'field:"speaker"' not in block
    assert 'field:"position_holder"' not in block
    assert "topRecordFieldShare" in RUNTIME
    assert "work-insight-pie" in RUNTIME
    assert not (ROOT / "web/src/components/WorkInsightsPanel.vue").exists()


def test_record_actions_group_citations_under_submenu():
    assert 'class="record-citation-menu"' in RUNTIME
    assert 'tr("ui.get_citation","Get Citation")' in RUNTIME
    assert 'data-cite-kind="inline"' in RUNTIME
    assert 'data-cite-kind="full"' in RUNTIME
    assert ".record-citation-popover" in STYLE


def test_search_defaults_are_exact_requested_columns_and_roomy_text_is_larger():
    assert 'global:["__db_status","work","page_start","needs_review","text"]' in RUNTIME
    assert '.search-result-table.roomy-results .textcell,.search-result-table.roomy-results .extracted-text-cell{font-size:14.5px!important' in STYLE


def test_search_routes_missing_database_to_creation_flow():
    assert RUNTIME.count('tr("search.redirect_database","Search needs a corpus database. Opening database creation now.")') >= 3
    assert RUNTIME.count("openDatabaseCreationFromResearch()") >= 4


def test_new_strings_are_bilingual():
    for key in (
        "ui.get_citation",
        "ui.inline",
        "ui.full",
        "dashboard.top_discourse_targets_work",
        "dashboard.discourse_roles_share_work",
        "works.other_values",
        "works.role_occurrences",
        "search.redirect_database",
    ):
        en = (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8")
        fr = (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8")
        assert f"'{key}'" in en or f'"{key}"' in en
        assert f"'{key}'" in fr or f'"{key}"' in fr

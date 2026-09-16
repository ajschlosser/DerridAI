from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/legacy/runtime.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "web/src/router/index.ts").read_text(encoding="utf-8")
VIEW = (ROOT / "web/src/views/RecordView.vue").read_text(encoding="utf-8")
EDIT = (ROOT / "web/src/components/record/RecordEditSheet.vue").read_text(encoding="utf-8")
READING = (ROOT / "web/src/components/record/RecordReadingPane.vue").read_text(encoding="utf-8")
HEADER = (ROOT / "web/src/components/record/RecordWorkspaceHeader.vue").read_text(encoding="utf-8")
SYSTEM = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")


def _dictionaries():
    tree = ast.parse(SYSTEM)
    found: dict[str, dict] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in {"DEFAULT_EN_US", "DEFAULT_FR_CA"}:
            found[node.target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "update" and isinstance(call.func.value, ast.Name) and call.func.value.id in {"DEFAULT_EN_US", "DEFAULT_FR_CA"} and len(call.args) == 1:
                found.setdefault(call.func.value.id, {}).update(ast.literal_eval(call.args[0]))
    return found


def test_record_player_release_version_is_consistent():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.35.12"
    assert 'version="0.35.12"' in MAIN
    assert "Corpus Viewer 0.35.12" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "DerridAI 0.35.12" in (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
    assert "## 0.35.10 — Record Player" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_record_route_is_vue_native_workspace():
    assert 'import RecordView from "../views/RecordView.vue"' in ROUTER
    assert 'path: "/record"' in ROUTER
    assert 'component: RecordView' in ROUTER
    assert 'view: "record", capability: "page.record", vueNative: true' in ROUTER
    for component in ("RecordWorkspaceHeader", "RecordReadingPane", "RecordInspector", "RecordEditSheet"):
        assert component in VIEW
    assert "LegacySurface" not in VIEW


def test_record_workspace_preserves_sparse_packets_and_avoids_history_payloads():
    start = RUNTIME.index("async function saveCurrentRecordChanges")
    end = RUNTIME.index("async function addCurrentRecordAnnotation", start)
    save_body = RUNTIME[start:end]
    assert 'field!=="updates"' in save_body
    assert '!String(field).startsWith("_")' in save_body
    assert "applyRecordChanges(file,index,safe" in save_body
    start = RUNTIME.index("function recordWorkspaceRecord")
    end = RUNTIME.index("function normalizedRecordAnnotation", start)
    projection = RUNTIME[start:end]
    assert 'delete out.updates' in projection
    assert 'delete out.annotations' in projection
    assert "compactRecordHistory" in RUNTIME


def test_record_workspace_role_and_feature_boundaries_remain_enforced():
    start = RUNTIME.index("async function currentRecordPrimaryAction")
    end = RUNTIME.index("function searchCurrentRecordMetadata", start)
    actions = RUNTIME[start:end]
    assert 'canUse("manageCorpus")' in actions
    assert 'canUse("editLocalRecords")' in actions
    assert 'canAccessPage("pdf")' in actions
    assert 'hasCapability("annotations.write")' in RUNTIME
    assert 'if(isResearcher()||!canUse("editLocalRecords"))' in RUNTIME


def test_record_reading_and_editing_are_accessible_native_components():
    assert '<dialog' in EDIT
    assert '<fieldset' in EDIT
    assert 'focus-visible' in EDIT
    assert 'focus-visible' in READING
    assert 'v-html' not in READING
    assert 'aria-label' in READING
    assert 'aria-expanded' in VIEW
    assert 'tabindex="-1"' not in VIEW or 'record-inspector-resizer' not in VIEW.split('tabindex="-1"')[0][-160:]
    assert 'record-id' in HEADER


def test_record_workspace_has_full_storybook_coverage_for_major_components():
    stories = {path.name for path in (ROOT / "web/src/components/record").glob("*.stories.ts")}
    expected = {
        "RecordWorkspaceHeader.stories.ts",
        "RecordReadingPane.stories.ts",
        "RecordProvenance.stories.ts",
        "RecordIndexTerms.stories.ts",
        "RecordAnnotations.stories.ts",
        "RecordPdfLinks.stories.ts",
        "RecordHistoryTimeline.stories.ts",
        "RecordInspector.stories.ts",
        "RecordEditSheet.stories.ts",
    }
    assert expected <= stories


def test_record_player_strings_have_english_quebec_french_parity():
    dictionaries = _dictionaries()
    en = dictionaries["DEFAULT_EN_US"]
    fr = dictionaries["DEFAULT_FR_CA"]
    assert set(en) == set(fr)
    for key in (
        "record.inspector", "record.tab_provenance", "record.focus_mode", "record.edit",
        "record.unsaved_fields", "record.quotation_provenance", "record.source_documents",
        "annotations.add_note", "record.change_history", "permissions.record_edit_denied",
    ):
        assert key in en and key in fr
        assert en[key].strip() and fr[key].strip()

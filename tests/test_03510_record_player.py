from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "web/src/router/index.ts").read_text(encoding="utf-8")
VIEW = (ROOT / "web/src/views/RecordView.vue").read_text(encoding="utf-8")
EDIT = (ROOT / "web/src/components/record/RecordEditSheet.vue").read_text(encoding="utf-8")
READING = (ROOT / "web/src/components/record/RecordReadingPane.vue").read_text(encoding="utf-8")
HEADER = (ROOT / "web/src/components/record/RecordWorkspaceHeader.vue").read_text(encoding="utf-8")
SYSTEM = ((ROOT / "api/app/system_store.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8"))
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")


def _dictionaries() -> dict[str, dict[str, str]]:
    def load(path: Path, variable: str) -> dict[str, str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                value = node.value
                if isinstance(target, ast.Name) and target.id == variable:
                    return ast.literal_eval(value)
        raise AssertionError(f"{variable} not found in {path}")
    return {
        "DEFAULT_EN_US": load(ROOT / "api/app/locales/en_us.py", "EN_US"),
        "DEFAULT_FR_CA": load(ROOT / "api/app/locales/fr_ca.py", "FR_CA"),
    }

def test_record_player_release_version_is_consistent():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.56.0"
    assert 'version="0.56.0"' in MAIN
    assert "Corpus Viewer 0.56.0" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "DerridAI 0.56.0" in (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
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

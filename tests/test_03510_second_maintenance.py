from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"web/src/App.vue").read_text(encoding="utf-8")
RUNTIME=(ROOT/"web/src/runtime/runtime.js").read_text(encoding="utf-8")
STYLE=(ROOT/"web/src/style.css").read_text(encoding="utf-8")
HEADER=(ROOT/"web/src/components/record/RecordWorkspaceHeader.vue").read_text(encoding="utf-8")
INSPECTOR=(ROOT/"web/src/components/record/RecordInspector.vue").read_text(encoding="utf-8")
PROVENANCE=(ROOT/"web/src/components/record/RecordProvenance.vue").read_text(encoding="utf-8")


def test_shell_does_not_false_gate_research_on_stale_database_snapshot():
    assert 'if(view==="rag"&&!s.value.hasCorpusDb)' not in APP
    assert 'if(view==="rag"&&!hasCorpusDb())' not in RUNTIME
    assert "authoritative store list" in APP
    assert "authoritative store refresh on entry" in RUNTIME


def test_researcher_static_profile_generation_is_normalized_server_side():
    if str(ROOT/"api") not in sys.path:
        sys.path.insert(0,str(ROOT/"api"))
    from app.main import _profile_generation_options
    values=_profile_generation_options({
        "num_ctx":"8192",
        "temperature":"0.2",
        "think":"false",
        "extra_options":'{"repeat_last_n": 128}',
        "keep_alive":"10m",
    })
    assert values["num_ctx"] == 8192
    assert values["temperature"] == 0.2
    assert values["think"] is False
    assert values["extra_options"] == {"repeat_last_n":128}
    assert values["keep_alive"] == "10m"


def test_toasts_and_operation_text_are_copyable_and_stay_above_shell():
    assert 'el.setAttribute("role","status")' in RUNTIME
    assert 'el.tabIndex=0' in RUNTIME
    assert 'el.onpointerenter=pause' in RUNTIME
    assert '#toast.toast{z-index:40000!important;pointer-events:auto!important;user-select:text!important' in STYLE
    assert '.operation-progress,.operation-progress-detail,.operation-toast-details,.operation-toast-grid,.operation-toast-events{user-select:text}' in STYLE


def test_record_title_shrinks_and_wraps_within_reason():
    assert "titleClass=computed" in HEADER
    assert "record-title-xlong" in HEADER
    assert "-webkit-line-clamp:2" in HEADER
    assert "white-space:nowrap" not in HEADER.split('.record-identity h1',1)[1].split('}',1)[0]


def test_record_inspector_avoids_horizontal_tab_and_provenance_scrolling():
    assert 'grid-template-columns:repeat(3,minmax(0,1fr))' in INSPECTOR
    assert 'overflow:auto' not in INSPECTOR.split('.record-inspector-tabs',1)[1].split('}',1)[0]
    assert "provenance-path" in PROVENANCE
    assert "provenance-chain" not in PROVENANCE
    assert "overflow:auto" not in PROVENANCE


def test_record_inspector_tabs_have_keyboard_and_aria_relationships():
    assert "onTabKeydown" in INSPECTOR
    assert "ArrowRight" in INSPECTOR and "ArrowLeft" in INSPECTOR
    assert "ArrowDown" in INSPECTOR and "ArrowUp" in INSPECTOR
    assert ':aria-controls="panelId(item[0])"' in INSPECTOR
    assert ':tabindex="tab===item[0]?0:-1"' in INSPECTOR
    assert ':aria-labelledby="tabId(\'overview\')"' in INSPECTOR


def test_response_faq_primary_grade_is_narrowed_to_component_prop_type():
    faq=(ROOT/"web/src/views/ResponseFaqView.vue").read_text(encoding="utf-8")
    assert 'function gradeScalar(value:unknown):string|number|null' in faq
    assert 'computed<string|number|null>' in faq
    assert 'return gradeScalar(value?.overall??value?.score)' in faq

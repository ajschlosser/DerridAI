from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
FAQ = (ROOT / "web/src/views/ResponseFaqView.vue").read_text(encoding="utf-8")
FAQ_LIST = (ROOT / "web/src/components/research/ResponseFaqList.vue").read_text(encoding="utf-8")
FAQ_ARCHIVE = (ROOT / "web/src/components/research/ResponseFaqArchiveDialog.vue").read_text(encoding="utf-8")
FAQ_SELECTION = (ROOT / "web/src/components/research/ResponseFaqSelectionBar.vue").read_text(encoding="utf-8")
PROVENANCE = (ROOT / "web/src/components/record/RecordProvenance.vue").read_text(encoding="utf-8")


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


def test_record_provenance_define_props_generic_is_well_formed():
    assert 'defineProps<{record:Record<string,unknown>}>();' in PROVENANCE
    assert 'defineProps<{record:Record<string,unknown>}();' not in PROVENANCE


def test_response_faq_gives_the_research_result_full_workspace_width():
    assert "ResponseFaqArchiveDialog" in FAQ
    assert "ResponseFaqSelectionBar" in FAQ
    assert "ResearchResultPresentation" in FAQ
    assert "response-faq-browser" not in FAQ
    assert "response-faq-layout" not in FAQ
    assert "activeEvidenceIndex" in FAQ
    assert "selected.value?.evidence" in FAQ
    assert "archiveOpen" in FAQ


def test_response_faq_archive_is_a_dialog_not_a_horizontal_carousel():
    assert '<dialog ref="dialog" class="response-archive-dialog"' in FAQ_ARCHIVE
    assert 'aria-labelledby="responseArchiveTitle"' in FAQ_ARCHIVE
    assert "ResponseFaqList" in FAQ_ARCHIVE
    assert "overflow-x:auto" not in FAQ_ARCHIVE
    assert "scroll-snap" not in FAQ_ARCHIVE
    assert "grid-auto-flow:column" not in FAQ_ARCHIVE
    assert "response-library-list" in FAQ_LIST
    assert "evidenceCount" in FAQ_LIST
    assert 'AppIcon name="books"' in FAQ_LIST


def test_response_faq_current_selection_is_compact_and_accessible():
    assert "faq.current_response" in FAQ_SELECTION
    assert "faq.browse_archive" in FAQ_SELECTION
    assert "response-selection-meta" in FAQ_SELECTION
    assert ":aria-label=" in FAQ_SELECTION
    assert ":focus-visible" in FAQ_SELECTION
    assert "@media(max-width:760px)" in FAQ_SELECTION
    assert "@media(prefers-reduced-motion:reduce)" in FAQ


def test_response_faq_polish_strings_have_english_quebec_french_parity():
    dictionaries = _dictionaries()
    en = dictionaries["DEFAULT_EN_US"]
    fr = dictionaries["DEFAULT_FR_CA"]
    assert set(en) == set(fr)
    for key in (
        "faq.library_title",
        "faq.library_help",
        "faq.archive_help",
        "faq.browse_archive",
        "faq.current_response",
        "faq.run_summary",
        "faq.retrieval_help",
        "faq.query_help",
        "faq.technical_metadata",
        "record.provenance_help",
        "record.attribution_path",
    ):
        assert key in en and key in fr
        assert en[key].strip() and fr[key].strip()


def test_new_result_and_faq_components_expand_storybook():
    stories={path.name for path in (ROOT/"web/src/components/research").glob("*.stories.ts")}
    assert "ResearchResultPresentation.stories.ts" in stories
    assert "ResponseFaqList.stories.ts" in stories
    assert "ResponseFaqArchiveDialog.stories.ts" in stories
    assert "ResponseFaqSelectionBar.stories.ts" in stories

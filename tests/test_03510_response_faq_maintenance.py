from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ((ROOT / "api/app/system_store.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/en_us.py").read_text(encoding="utf-8") + "\n" + (ROOT / "api/app/locales/fr_ca.py").read_text(encoding="utf-8"))
FAQ = (ROOT / "web/src/views/ResponseFaqView.vue").read_text(encoding="utf-8")
FAQ_LIST = (ROOT / "web/src/components/research/ResponseFaqList.vue").read_text(encoding="utf-8")
FAQ_ARCHIVE = (ROOT / "web/src/components/research/ResponseFaqArchiveDialog.vue").read_text(encoding="utf-8")
FAQ_SELECTION = (ROOT / "web/src/components/research/ResponseFaqSelectionBar.vue").read_text(encoding="utf-8")
PROVENANCE = (ROOT / "web/src/components/record/RecordProvenance.vue").read_text(encoding="utf-8")


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






def test_response_faq_question_finder_prioritizes_question_scanning():
    assert "faq.find_question" in FAQ
    assert "faq.current_question" in FAQ_SELECTION
    assert "faq.find_another_question" in FAQ_SELECTION
    assert "faq.questions_label" in FAQ_ARCHIVE
    assert ':search="search"' in FAQ_ARCHIVE
    assert "highlightParts" in FAQ_LIST
    assert "<mark" in FAQ_LIST
    assert "response-library-question-icon" in FAQ_LIST

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
ROUTER = (ROOT / "web/src/router/index.ts").read_text(encoding="utf-8")
RESEARCH = (ROOT / "web/src/views/ResearchView.vue").read_text(encoding="utf-8")
FAQ = (ROOT / "web/src/views/ResponseFaqView.vue").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "web/src/components/research/ResearchResultPresentation.vue").read_text(encoding="utf-8")
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

def test_release_version_0355_is_consistent():
    package=json.loads((ROOT/"web/package.json").read_text(encoding="utf-8"))
    assert package["version"]=="0.57.6"
    assert 'version="0.57.6"' in MAIN
    assert "Corpus Viewer 0.57.6" in (ROOT/"web/index.html").read_text(encoding="utf-8")
    assert "DerridAI 0.57.6" in (ROOT/"web/src/App.vue").read_text(encoding="utf-8")
    assert "0.35.5 — RAGety Anne" in (ROOT/"README.md").read_text(encoding="utf-8")


def test_operations_open_rag_results_in_native_research_workspace():
    start=RUNTIME.index("async function openRagResult")
    end=RUNTIME.index("async function getResponseFaqPage",start)
    body=RUNTIME[start:end]
    assert '/rag?job=' in body
    assert 'urlSyncHook' in body
    assert 'rag-result-dialog' not in body
    assert 'route.query.job' in RESEARCH
    assert 'runtime.getResearchJob(requestedJobId)' in RESEARCH


def test_response_faq_is_native_and_reuses_same_result_presentation():
    assert 'ResponseFaqView' in ROUTER
    assert 'component: ResponseFaqView' in ROUTER
    assert 'ResearchResultPresentation' in FAQ
    assert 'ResearchResultPresentation' in RESEARCH
    assert 'ResearchAnswerWorkspace' in PRESENTATION
    assert 'ResearchEvidencePanel' in PRESENTATION
    assert 'activeEvidenceIndex' in FAQ
    assert 'record.evidence' in FAQ


def test_response_faq_retains_search_paging_rerun_grade_and_provenance():
    assert 'getResponseFaqPage' in RUNTIME
    assert 'gradeResponseFaqRecord' in RUNTIME
    assert 'rerunResponseFaqRecord' in RUNTIME
    for token in ('search','pageSize','savedGrades','selected.retrieval','selected.query_metadata'):
        assert token in FAQ


def test_toasts_and_operation_notifications_stack_above_sidebar():
    assert '.shell-sidebar{z-index:500!important' in STYLE
    assert '#toast.toast{z-index:12000!important' in STYLE
    assert '.operation-progress-stack{z-index:11000!important' in STYLE


def test_new_result_and_faq_components_expand_storybook():
    stories={path.name for path in (ROOT/"web/src/components/research").glob("*.stories.ts")}
    assert "ResearchResultPresentation.stories.ts" in stories
    assert "ResponseFaqList.stories.ts" in stories


def test_new_faq_strings_have_english_quebec_french_parity():
    dictionaries=_dictionaries()
    en=dictionaries["DEFAULT_EN_US"]
    fr=dictionaries["DEFAULT_FR_CA"]
    assert set(en)==set(fr)
    for key in (
        "faq.page_kicker","faq.page_subtitle","faq.saved_responses","faq.run_provenance",
        "research.retrieval_diagnostics","research.query_metadata","permissions.faq_denied",
    ):
        assert key in en and key in fr
        assert en[key] and fr[key]

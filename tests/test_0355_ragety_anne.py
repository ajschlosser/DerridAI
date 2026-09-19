from __future__ import annotations

import ast
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





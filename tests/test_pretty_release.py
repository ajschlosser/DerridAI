from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
AUTH = (ROOT / "api/app/auth.py").read_text(encoding="utf-8")
VIEW = (ROOT / "web/src/views/ResearchView.vue").read_text(encoding="utf-8")
ANSWER = (ROOT / "web/src/components/research/ResearchAnswerWorkspace.vue").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "web/src/components/research/ResearchEvidencePanel.vue").read_text(encoding="utf-8")
SETTINGS = (ROOT / "web/src/components/research/ResearchSettingsDrawer.vue").read_text(encoding="utf-8")
COMPOSER = (ROOT / "web/src/components/research/ResearchComposer.vue").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "web/src/components/research/ResearchResultPresentation.vue").read_text(encoding="utf-8")


def _translation_dicts() -> dict[str, dict[str, str]]:
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

def test_release_version_and_title_0310():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.57.6"
    assert 'version="0.57.6"' in MAIN
    assert "Corpus Viewer 0.57.6" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "0.31.0 — The Pretty Release" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_research_is_native_vue_workspace_not_legacy_surface():
    assert "ResearchComposer" in VIEW
    assert "ResearchResultPresentation" in VIEW
    assert "ResearchAnswerWorkspace" in PRESENTATION
    assert "ResearchEvidencePanel" in PRESENTATION
    assert "ResearchSettingsDrawer" in VIEW
    assert "ResearchRunsDrawer" in VIEW
    assert '<RuntimeSurface v-if="!isNativeResearch"' in VIEW
    assert 'route.name==="rag"' in VIEW
    assert "openRagResult" not in VIEW


def test_answer_is_inline_and_evidence_is_persistent_two_pane_workspace():
    assert "research-workspace-grid" in PRESENTATION
    assert "grid-template-columns:minmax(0,2.15fr)" in STYLE
    assert "position:sticky" in STYLE and ".research-evidence-panel" in STYLE
    assert "result?.answer" in ANSWER
    assert "research-answer-prose" in ANSWER
    assert "research-evidence-inspector" in EVIDENCE
    assert "speaker" in EVIDENCE and "position_holder" in EVIDENCE and "stance" in EVIDENCE
    assert "proposition_status" in EVIDENCE


def test_primary_research_flow_uses_progressive_disclosure():
    assert "sourceCollection" in COMPOSER
    assert "providerProfileId" in COMPOSER
    assert "responseLanguage" in COMPOSER
    assert "preset" in COMPOSER
    assert "Recent questions" in COMPOSER
    assert "Expert settings" in COMPOSER
    assert "research-settings-dialog" in SETTINGS
    assert "k_help" in SETTINGS and "fetch_k_help" in SETTINGS
    assert "Advanced generation parameters" not in COMPOSER


def test_new_research_components_do_not_use_legacy_tiny_buttons():
    for path in [ROOT / "web/src/views/ResearchView.vue", *sorted((ROOT / "web/src/components/research").glob("*.vue"))]:
        assert "btn tiny" not in path.read_text(encoding="utf-8")
    assert "min-height:44px" in STYLE  # primary Research action
    assert ".research-text-action{min-height:32px" in STYLE


def test_research_preserves_role_and_capability_boundaries():
    assert 'auth.can("rag.run")' in VIEW
    assert 'auth.can("rag.jobs.own")' in VIEW
    assert "auth.can('evidence.select')" in VIEW
    assert "auth.isAdmin" in VIEW  # admin-only manual grading launcher
    assert '"page.research"' in AUTH
    assert '"rag.run"' in AUTH
    assert '"rag.jobs.own"' in AUTH
    assert '"evidence.select"' in AUTH
    assert '"providers.researcher.use"' in AUTH
    # Owned job reads are available to a role allowed to start Research while
    # history/cancel/delete remain behind the separate management permission.
    assert 'method == "GET"' in MAIN and '"rag.run"' in MAIN and '"rag.jobs.own"' in MAIN
    assert "_researcher_job_access" in MAIN


def test_research_bridge_stays_sparse_and_does_not_leak_credentials():
    for name in (
        "getResearchWorkspaceSnapshot", "updateResearchConfig", "removeResearchEvidence",
        "clearResearchEvidence", "discoverResearchModels", "refreshResearchJobs",
        "getResearchJob", "startResearchRun", "prepareResearchRerun",
    ):
        assert name in RUNTIME
    profile_start = RUNTIME.index("function researchProfileForUi")
    profile_end = RUNTIME.index("function researchEvidenceForUi", profile_start)
    profile_bridge = RUNTIME[profile_start:profile_end]
    assert "api_key" not in profile_bridge
    assert "base_url" not in profile_bridge
    run_start = RUNTIME.index("async function startResearchRun")
    run_end = RUNTIME.index("async function gradeResearchJob", run_start)
    run_bridge = RUNTIME[run_start:run_end]
    assert "selectedEvidencePayload()" in run_bridge
    assert 'base_url:isResearcher()?null' in run_bridge
    assert 'api_key:isResearcher()?null' in run_bridge
    assert "updates" not in run_bridge


def test_selected_evidence_has_compact_inspectable_metadata_but_transport_is_ids():
    assert "text_preview" in RUNTIME
    assert '.slice(0,280)' in RUNTIME
    assert "proposition_status" in RUNTIME
    payload_start = RUNTIME.index("function selectedEvidencePayload")
    payload_end = RUNTIME.index("function evidenceButtonHtml", payload_start)
    payload = RUNTIME[payload_start:payload_end]
    assert "{collection:item.collection,chroma_id:item.chroma_id}" in payload
    assert "text_preview" not in payload
    assert "research-selected-details" in EVIDENCE


def test_evidence_only_state_clears_when_selection_becomes_empty():
    assert "if(!selectedEvidenceEntries().length)state.ragConfig.skip_retrieval=false" in RUNTIME
    assert "state.ragConfig.skip_retrieval=false" in RUNTIME
    assert 'if(!evidence.length&&preset.value==="evidence")applyPreset("balanced")' in VIEW


def test_researcher_generation_controls_are_locked_and_server_profile_is_authoritative():
    assert ':disabled="researcher"' in SETTINGS
    assert "researcher_profile_locked" in SETTINGS
    assert 'v-if="!researcher"' in SETTINGS
    assert 'base_url:isResearcher()?null' in RUNTIME
    assert 'api_key:isResearcher()?null' in RUNTIME


def test_accessibility_semantics_and_responsive_research_layout():
    assert "<dialog" in SETTINGS
    assert "@cancel.prevent" in SETTINGS
    assert "aria-labelledby" in VIEW
    assert "aria-live=\"polite\"" in ANSWER
    assert "focus-visible" in STYLE
    assert "@media(max-width:860px)" in STYLE
    assert "@media(max-width:560px)" in STYLE
    assert "research-settings-error" in SETTINGS and 'role="alert"' in SETTINGS


def test_all_native_research_strings_exist_in_english_and_french():
    keys: set[str] = set()
    paths = [ROOT / "web/src/views/ResearchView.vue", *sorted((ROOT / "web/src/components/research").glob("*.vue"))]
    for path in paths:
        keys.update(re.findall(r"i18n\.t\(['\"]([^'\"]+)", path.read_text(encoding="utf-8")))
    dictionaries = _translation_dicts()
    assert set(dictionaries) == {"DEFAULT_EN_US", "DEFAULT_FR_CA"}
    for dictionary in dictionaries.values():
        assert not (keys - set(dictionary))


def test_storybook_has_native_research_component_coverage():
    stories = sorted((ROOT / "web/src/components/research").glob("*.stories.ts"))
    names = {path.name for path in stories}
    assert {
        "ResearchComposer.stories.ts",
        "ResearchEvidencePanel.stories.ts",
        "ResearchAnswerWorkspace.stories.ts",
        "ResearchSettingsDrawer.stories.ts",
        "ResearchRunsDrawer.stories.ts",
    }.issubset(names)


def test_research_evidence_bridge_narrows_nullable_items_for_typescript():
    # researchEvidenceForUi intentionally returns null for empty input. Use an
    # explicit predicate rather than filter(Boolean) so TypeScript can narrow
    # the array before it crosses the Vue workspace boundary.
    assert RUNTIME.count("map(researchEvidenceForUi).filter(item=>item!==null)") >= 2

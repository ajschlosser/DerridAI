from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0406_release_identity_and_notes():
    package = json.loads(text("web/package.json"))
    assert package["version"] == "0.50.1"
    assert 'version="0.50.1"' in text("api/app/main.py")
    assert 'APP_VERSION = "0.50.1"' in text("api/app/config.py")
    assert "0.50.1 — Ignoble Insect" in text("README.md")


def test_pdf_workspace_defaults_to_builder_and_explorer_is_secondary():
    workspace = text("web/src/views/PdfWorkspaceView.vue")
    dictionary = text("api/app/locales/en_us.py") + text("api/app/locales/fr_ca.py")
    assert 'route.query.mode==="explorer"?"explorer":"builder"' in workspace
    assert workspace.index("mode==='builder'") < workspace.index("mode==='explorer'")
    assert '<PdfCorpusBuilder v-if="mode===\'builder\'" />' in workspace
    assert 'nav.pdf' in dictionary and 'Corpus Builder' in dictionary
    assert 'Générateur de corpus' in dictionary


def test_explorer_specific_actions_still_open_the_secondary_explorer_tab():
    runtime = text("web/src/runtime/runtime.js")
    app = text("web/src/App.vue")
    assert 'function openPdfExplorerWorkspace()' in runtime
    assert 'path:"/pdf?mode=explorer"' in runtime
    assert 'openLoadedPdfPage(page)' in runtime
    assert 'runtime.navigateView(runtimeView,path)' in app
    assert 'function syncUrl({replace=false,href=null}={})' in runtime
    assert '@param {string} [href=""]' in runtime
    assert 'function navigateView(view,href="")' in runtime


def test_home_has_dedicated_corpus_build_card_and_initial_jobs_refresh_rerenders_it():
    runtime = text("web/src/runtime/runtime.js")
    style = text("web/src/style.css")
    assert "function renderCorpusBuildsHomeCard()" in runtime
    assert '${renderCorpusBuildsHomeCard()}' in runtime
    assert 'job.type==="pdf_corpus"' in runtime
    assert 'id="dashCorpusBuilder"' in runtime
    assert 'data-dashboard-corpus-build=' in runtime
    refresh = runtime.index('await refreshJobs({rerender:false});')
    rerender = runtime.index('if(state.view==="home"&&document.querySelector("#main"))renderDashboard(document.querySelector("#main"));', refresh)
    polling = runtime.index("startJobPolling();", rerender)
    assert refresh < rerender < polling
    assert "refreshCorpusBuildsHomeCardOnly()" in runtime
    assert "wireCorpusBuildsHomeCard(main)" in runtime
    assert ".dashboard-corpus-builds" in style
    assert ".dashboard-corpus-row" in style


def test_provider_setup_is_streamlined_and_current_profile_is_server_owned():
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    selector = text("web/src/components/ProviderProfileSelect.vue")
    models = text("api/app/models.py")
    dictionary = text("api/app/locales/en_us.py") + text("api/app/locales/fr_ca.py")
    assert "provider-area" in builder and "setup-card-heading" in builder
    assert "escalation-field" in builder
    assert "build-launch-row" in builder
    assert "provider-summary-card" in selector
    assert "provider-stat-group" in selector
    assert ':context-label="i18n.t(\'providers.context_tokens\',\'context tokens\')"' in builder
    assert 'profile_id:"derrida-scholarly-v5"' not in builder
    assert 'default="derrida-scholarly-v11"' in models
    assert 'pdf_corpus.provider_profile' in dictionary and 'Provider profile' in dictionary and 'Profil fournisseur' in dictionary


def test_retry_ui_hides_blocked_action_while_build_is_running_and_syncs_rail():
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    api = text("web/src/api/pdfCorpus.ts")
    assert "retrying_segmentation?: boolean" in api
    assert "const segmentationNeedsReview=computed" in builder
    assert "const retryingSegmentation=computed(()=>Boolean(buildRunning.value" in builder
    assert 'v-if="retryingSegmentation"' in builder
    assert 'v-if="segmentationNeedsReview&&(!showReviewWorkspace||finishPhase)"' in builder
    assert "boundary decision(s) to review" in text("web/src/components/CorpusBuildProgress.vue")
    assert "function syncBuildInRail(build:CorpusBuild)" in builder
    assert "syncBuildInRail(currentBuild.value)" in builder
    assert "registerBuildOperation(currentBuild.value)" in builder
    assert "registerExternalJob" in builder
    assert "watch(()=>route.query.build" in builder
    assert "This build is already running. Its live status is shown below." in builder


def test_retry_state_is_explicit_in_backend_operations():
    builder = text("api/app/corpus_builder.py")
    assert 'build["retrying_segmentation"] = bool(build.get("segmentation_blocked"))' in builder
    assert 'f"Retrying {len(unresolved)} unresolved segmentation region(s)"' in builder
    assert 'retrying_segmentation=False' in builder
    assert 'Resume is intentionally idempotent while work is active' in builder
    assert 'if build.get("status") in {"queued", "running"}' in builder


def test_0406_new_strings_exist_in_english_and_quebec_french():
    dictionary = text("api/app/locales/en_us.py") + text("api/app/locales/fr_ca.py")
    for key in (
        "pdf_corpus.retry_in_progress",
        "pdf_corpus.build_stopped_title",
        "pdf_corpus.home_title",
        "pdf_corpus.open_builder",
        "providers.context_tokens",
    ):
        assert dictionary.count(key) >= 2

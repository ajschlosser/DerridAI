from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dundee_queue_tabs_use_explicit_numeric_counts():
    text = (ROOT / "web/src/components/CorpusReviewQueueTabs.vue").read_text()
    assert "function tabCount(id:ReviewQueue):number" in text
    assert "props[tab.count]" not in text
    assert "sourceProblems?:number" in text


def test_dundee_storybook_stories_import_declared_adapter_package():
    for name in ("CorpusBuildStageNotice.stories.ts", "CorpusReviewQueueTabs.stories.ts"):
        text = (ROOT / "web/src/components" / name).read_text()
        assert 'from "@storybook/vue3-vite"' in text


def test_dundee_active_build_summary_avoids_inline_unknown_record_access():
    text = (ROOT / "web/src/components/PdfCorpusBuilder.vue").read_text()
    assert "activeProviderProfileLabel" in text
    assert "(currentBuild.request||{}).provider_profile_id" not in text

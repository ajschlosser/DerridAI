from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_corpus_build_frontend_contract_includes_source_block_count():
    api_contract = (ROOT / "web/src/api/pdfCorpus.ts").read_text(encoding="utf-8")
    lifecycle = (ROOT / "web/src/components/CorpusBuildLifecycleCard.vue").read_text(encoding="utf-8")
    assert "source_block_count?: number" in api_contract
    assert "props.build.source_block_count" in lifecycle

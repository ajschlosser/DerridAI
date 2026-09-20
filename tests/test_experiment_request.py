from app.models import PdfCorpusRecordRerun


def test_experiment_block_validates_and_rejects_unknown_ablations():
    body = PdfCorpusRecordRerun(experiment={"ablations": ["autofill"], "arms": [{"name": "A"}, {"name": "B", "ablations": ["rejection_memory"]}], "blind_rate": 0.1})
    dumped = body.model_dump(exclude_none=True)["experiment"]
    assert dumped["arms"][1]["ablations"] == ["rejection_memory"] and dumped["blind_rate"] == 0.1
    import pytest
    with pytest.raises(ValueError):
        PdfCorpusRecordRerun(experiment={"ablations": ["nonsense"]})
    with pytest.raises(ValueError):
        PdfCorpusRecordRerun(experiment={"blind_rate": 2})


def test_a_provider_profile_with_high_concurrency_no_longer_breaks_text_touchup():
    # A FreeLLM / OpenAI-compatible profile defaults to 32 parallel requests; the request was rejected with a 422.
    from app.models import PdfCorpusBuildCreate, PdfCorpusTextTouchupRequest

    body = PdfCorpusTextTouchupRequest(provider="openai", model="auto", max_concurrent_requests=32, provider_profile_id="openai-1")
    assert body.max_concurrent_requests == 16
    assert PdfCorpusTextTouchupRequest(max_concurrent_requests=0).max_concurrent_requests == 1
    assert PdfCorpusRecordRerun(max_concurrent_requests=99).max_concurrent_requests == 16
    assert PdfCorpusBuildCreate(asset_id="a", max_concurrent_requests=40).max_concurrent_requests == 16

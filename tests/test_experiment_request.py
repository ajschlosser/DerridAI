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

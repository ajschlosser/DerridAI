# Copyright 2026 Aaron John Schlosser, PhD.
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import unit_policy as up  # noqa: E402

TEXT = "Dr. Derrida wrote Of Grammatology in 1967. It was not, however, the first. Was it? Yes! See p. 32 and fig. 3.5 for details."


def test_sentences_respect_abbreviations_and_conserve_text():
    parts = up.split_sentences(TEXT)
    assert len(parts) == 5
    assert "".join(parts) == TEXT
    assert parts[0].startswith("Dr. Derrida") and parts[0].strip().endswith("1967.")


def test_lines_and_windows_conserve_text():
    text = "line one\nline two\n\nline three"
    assert "".join(up.split_lines(text)).replace("\n", "") == text.replace("\n", "")
    windows = up.split_chars(TEXT, 60)
    assert "".join(windows) == TEXT and all(len(w) <= 60 for w in windows)


@pytest.mark.parametrize("policy", [{"mode": "sentence"}, {"mode": "line"}, {"mode": "chars", "chars": 80}])
def test_apply_keeps_locators_and_conserves_text(policy):
    blocks = [
        {"block_id": "p1-b1", "page": 3, "type": "paragraph", "text": TEXT + "\nAnother line follows here.", "speaker": "X", "bbox": [0, 0, 1, 1]},
        {"block_id": "p1-b2", "page": 3, "type": "heading", "text": "Chapter I. The Beginning."},
        {"block_id": "p1-b3", "page": 3, "type": "header_footer", "text": "32", "excluded_reason": "page_number"},
    ]
    derived, remap = up.apply_unit_policy(blocks, policy)
    kids = [b for b in derived if b.get("parent_block_id") == "p1-b1"]
    assert len(kids) > 1 and all(k["page"] == 3 and k["speaker"] == "X" for k in kids)
    assert " ".join(k["text"] for k in kids).split() == blocks[0]["text"].split()
    assert [b["block_id"] for b in derived if b["block_id"] in {"p1-b2", "p1-b3"}] == ["p1-b2", "p1-b3"]
    assert remap[0] == [k["block_id"] for k in kids]


def test_default_and_paragraph_leave_blocks_alone():
    blocks = [{"block_id": "a", "page": 1, "type": "paragraph", "text": TEXT}]
    for mode in ("default", "paragraph"):
        derived, _ = up.apply_unit_policy(blocks, {"mode": mode})
        assert derived == blocks


def test_policy_validation():
    with pytest.raises(ValueError):
        up.normalize_policy({"mode": "haiku"})
    with pytest.raises(ValueError):
        up.normalize_policy({"mode": "chars", "chars": 5})
    with pytest.raises(ValueError):
        up.normalize_policy({"mode": "chars"})
    assert up.normalize_policy({"mode": "chars", "chars": "300"}) == {"mode": "chars", "chars": 300}


def test_preview_reports_counts_and_samples():
    blocks = [{"block_id": "a", "page": 1, "type": "paragraph", "text": TEXT}]
    result = up.preview(blocks, {"mode": "sentence"})
    assert result["unit_count"] == 5 and result["source_block_count"] == 1
    assert result["sample"][0]["block_id"] == "a-u001"


def test_repository_derives_a_sentence_asset_and_keeps_the_original(tmp_path):
    from app import corpus_builder as cb

    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    text = "\n\n".join([TEXT, "Second paragraph is short. It has two sentences."])
    original = repo.save_asset(text.encode(), filename="essay.txt")
    derived = repo.derive_asset_with_units(original["asset_id"], {"mode": "sentence"})
    assert derived["asset_id"] != original["asset_id"]
    assert derived["derived_from_asset_id"] == original["asset_id"]
    assert derived["sha256"] == original["sha256"]
    blocks = repo.load_blocks(derived["asset_id"])
    assert len(blocks) == 7 and derived["block_count"] == 7
    assert " ".join(b["text"] for b in blocks).split() == text.split()
    page_ids = [i for page in derived["pages"] for i in page["block_ids"]]
    assert page_ids == [b["block_id"] for b in blocks]
    # The original is unchanged, and asking for the default again returns it.
    assert len(repo.load_blocks(original["asset_id"])) == 2
    assert repo.derive_asset_with_units(derived["asset_id"], {"mode": "default"})["asset_id"] == original["asset_id"]
    # Idempotent: the same policy yields the same asset.
    assert repo.derive_asset_with_units(original["asset_id"], {"mode": "sentence"})["asset_id"] == derived["asset_id"]

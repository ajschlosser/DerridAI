# Copyright 2026 Aaron John Schlosser, PhD.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.corpus_segmentation import (  # noqa: E402
    _deterministic_boundary_candidates,
    _seam_quality,
)
from app.language_segmentation import (  # noqa: E402
    looks_like_speaker_start,
    looks_like_strong_heading,
    profile_metadata,
    split_sentences,
    starts_mid_sentence_text,
)
from app.sentence_boundaries import clean_boundary, snap_boundaries_to_sentences  # noqa: E402
from app.source_text import html_to_text, leading_speaker  # noqa: E402
from app.unit_policy import apply_unit_policy  # noqa: E402


def _blocks(*texts: str, kind: str = "body") -> list[dict[str, object]]:
    return [
        {"block_id": f"b{index}", "text": text, "type": kind, "page": 1}
        for index, text in enumerate(texts)
    ]


def test_sentence_splitter_conserves_cjk_without_spaces() -> None:
    text = "这是第一句。这是第二句！第三句？"
    parts = split_sentences(text, "zh")
    assert parts == ["这是第一句。", "这是第二句！", "第三句？"]
    assert "".join(parts) == text

    japanese = "これは一文です。次の文です。"
    assert "".join(split_sentences(japanese, "ja")) == japanese
    assert len(split_sentences(japanese, "ja")) == 2


def test_sentence_splitter_handles_arabic_and_indic_terminators() -> None:
    arabic = "هذه جملة؟هذه جملة أخرى."
    assert split_sentences(arabic, "ar") == ["هذه جملة؟", "هذه جملة أخرى."]

    hindi = "यह पहला वाक्य है। यह दूसरा वाक्य है॥"
    parts = split_sentences(hindi, "hi")
    assert len(parts) == 2
    assert "".join(parts) == hindi


def test_sentence_splitter_preserves_language_specific_abbreviations() -> None:
    russian = "Проф. Деррида пишет здесь. Затем следует другой тезис."
    parts = split_sentences(russian, "ru")
    assert len(parts) == 2
    assert parts[0].startswith("Проф. Деррида")


def test_script_fallback_is_segmentation_only_and_conservative() -> None:
    chinese = "第一句。第二句。"
    metadata = profile_metadata(None, chinese)
    assert metadata["profile"] == "zh"
    assert metadata["language_source"] == "script_inference"
    assert len(split_sentences(chinese)) == 2
    # Caseless scripts are not declared to continue a sentence merely because
    # their first character lacks uppercase/lowercase morphology.
    assert not starts_mid_sentence_text("第二句。", "zh")


def test_language_aware_heading_and_speaker_signals() -> None:
    assert looks_like_strong_heading("第一章 解构", "zh")
    assert looks_like_strong_heading("Глава 2", "ru")
    assert looks_like_strong_heading("الفصل الأول", "ar")
    assert looks_like_speaker_start("デリダ：テクストが始まる", "ja")
    assert looks_like_speaker_start("دريدا: يبدأ النص", "ar")


def test_semantic_candidates_use_document_language() -> None:
    blocks = [
        {"block_id": "b0", "text": "前の節はここで終わる。", "type": "body"},
        {"block_id": "b1", "text": "第一章 解构", "type": "heading"},
        {"block_id": "b2", "text": "デリダ：テクストが始まる", "type": "body"},
    ]
    candidates = _deterministic_boundary_candidates(blocks, {}, "ja")
    assert candidates[0]["signals"] == ["heading_start", "strong_heading_start"]
    assert "speaker_label" in candidates[1]["signals"]


def test_seam_quality_recognizes_non_latin_sentence_end() -> None:
    left = {"block_id": "b0", "text": "यह एक वाक्य है।", "type": "body"}
    right = {"block_id": "b1", "text": "यह अगला वाक्य है।", "type": "body"}
    score, protected, signals = _seam_quality(left, right, "hi")
    assert not protected
    assert score >= 0.55
    assert "sentence_end" in signals


def test_sentence_boundary_snap_uses_cjk_terminators() -> None:
    blocks = _blocks("第一句。", "第二句", "继续。")
    boundaries = [{"after_block_id": "b1", "decision": "split"}]
    moved, report = snap_boundaries_to_sentences(
        blocks,
        boundaries,
        language="zh",
    )
    assert moved[0]["after_block_id"] == "b0"
    assert report["moved"] == [{"from": "b1", "to": "b0"}]
    assert clean_boundary(blocks[0], blocks[1], "zh")


def test_automatic_unit_policy_uses_language_profile() -> None:
    text = "第一句很长但仍然完整。" * 8 + "第二句也应该被识别。" * 8
    blocks = [{"block_id": "p1-b1", "page": 1, "type": "paragraph", "text": text}]
    derived, _ = apply_unit_policy(
        blocks,
        {"mode": "auto", "max_chars": 60, "language": "zh"},
    )
    assert len(derived) > 1
    assert "".join(block["text"] for block in derived).replace(" ", "") == text.replace(" ", "")


def test_abbreviation_sensitive_boundary_is_not_treated_as_a_sentence_end() -> None:
    left = {"block_id": "b0", "text": "Dr.", "type": "body"}
    right = {"block_id": "b1", "text": "Derrida continues the sentence.", "type": "body"}
    assert not clean_boundary(left, right, "en")


def test_html_lang_is_preserved_as_documentary_language_metadata() -> None:
    text, metadata = html_to_text("<html lang=\"ja\"><body><p>第一文。</p></body></html>")
    assert text == "第一文。"
    assert metadata["language"] == "ja"


def test_ingest_speaker_detection_accepts_non_latin_labels() -> None:
    assert leading_speaker("デリダ：テクストが始まる") == "デリダ"
    assert leading_speaker("دريدا: يبدأ النص") == "دريدا"

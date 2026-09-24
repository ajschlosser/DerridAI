# Copyright 2026 Aaron John Schlosser, PhD.
"""Language-agnostic text-noise scoring and raster DPI mapping.

Why: OCR that still looks like letters (vEignes, C111.11.31.CS) used to miss the
10% unusable-source gate. Word-shape noise and scan DPI must flag it without a
language dictionary, and an LLM may only raise the deterministic score.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.models import PdfCorpusBuildCreate
from app.raster_quality import noise_from_effective_dpi
from app.source_quality import assess_extracted_source
from app.text_noise import (
    DEFAULT_NOISE_THRESHOLD,
    annotate_records,
    blend_noise_scores,
    raster_score_for_pages,
    score_text_noise,
    should_ask_llm,
)

GARBLED = """rouge, c'est le res.c;ic, rornrne le t•ail:lit justement K]ossowski. lc reickur sur ellesini;mies des vEignes quand elks rencontrent des C111.11.31.CS de rockers Oil (11.:CHeS sc. hrisent
Brand itself also :iignifics Thu mark lcft by a burning branding iron. Ir is the seething surf
e.Pvrim1;—frorn all sides there is howling, t]Srealuning, crying, and screaming, at 1110,
SiliS 341551 l'eperonl — cc ne sont gitc hurlernents, nicnaces, CTiS StriClUtIlS
U'est pas Si 11.)in 4.-Cinunc mugissant tatireakt: cc faisarkt, de satin pied d'ebratfleur
"""

CLEAN = (
    "La différance n'est pas un présent-étant. Brand itself also signifies the mark "
    "left by a burning branding iron. It is the seething surf, the waves rolling back "
    "over themselves as they crash against the rocky shoreline. Klossowski writes of "
    "the spur [l'éperon] while Nietzsche's earth-shaker sings his aria."
)


def test_garbled_ocr_is_unusable_at_default_threshold() -> None:
    """The facing-page OCR soup from a damaged text layer exceeds the default 45% bar."""
    report = score_text_noise(GARBLED)
    assert report["score"] >= DEFAULT_NOISE_THRESHOLD
    assert report["dirty_token_ratio"] > 0.1
    assert "interior_punct" in report["reasons"] or "letter_digit_mix" in report["reasons"]


def test_bilingual_scholarly_prose_stays_legible() -> None:
    """French, English, names, and hyphenation must not count as trash."""
    report = score_text_noise(CLEAN)
    assert report["score"] < DEFAULT_NOISE_THRESHOLD
    rows = [{"record_id": "clean", "text": CLEAN}, {"record_id": "garbled", "text": GARBLED}]
    annotate_records(rows, threshold=DEFAULT_NOISE_THRESHOLD)
    assert rows[0]["text_noise"]["unusable"] is False
    assert rows[1]["text_noise"]["unusable"] is True
    assert rows[1]["text_noise"]["score"] >= DEFAULT_NOISE_THRESHOLD


def test_llm_may_only_raise_noise() -> None:
    assert blend_noise_scores(80, llm_score=10, llm_confidence=0.99) == 80


def test_record_raster_noise_uses_typical_page_quality_not_single_worst_page() -> None:
    record = {"pdf_pages": [1, 2, 3]}
    pages = [
        {"pdf_page": 1, "raster": {"noise": 8}},
        {"pdf_page": 2, "raster": {"noise": 12}},
        {"pdf_page": 3, "raster": {"noise": 92}},
    ]

    assert raster_score_for_pages(record, pages) == 12
    assert blend_noise_scores(40, llm_score=70, llm_confidence=0.7) == 70
    assert blend_noise_scores(40, llm_score=70, llm_confidence=0.2) == 40
    assert should_ask_llm(10) is False
    assert should_ask_llm(50) is True


def test_low_embedded_dpi_is_noisy_high_dpi_is_clean() -> None:
    assert noise_from_effective_dpi(72) >= 70
    assert noise_from_effective_dpi(300) == 0
    pages = [{"pdf_page": 1, "raster": {"noise": 80, "effective_dpi": 72}}]
    rows = [{"record_id": "r", "text": CLEAN, "pdf_pages": [1]}]
    annotate_records(rows, pages=pages, threshold=45)
    assert rows[0]["text_noise"]["raster_score"] == 80
    assert rows[0]["text_noise"]["unusable"] is True
    assert "low_raster_quality" in rows[0]["text_noise"]["reasons"]


def test_build_request_defaults_keep_noise_tuning_off_the_llm() -> None:
    assert PdfCorpusBuildCreate(asset_id="a").llm_assess_text_noise is False
    assert PdfCorpusBuildCreate(asset_id="a").noise_unusable_threshold == DEFAULT_NOISE_THRESHOLD


def test_extracted_source_is_scored_before_a_build() -> None:
    """Page noise is available as soon as blocks exist, without constructing records."""
    report = assess_extracted_source(
        [{"page": 1, "text": GARBLED, "extraction_method": "ocr"}],
        [{"pdf_page": 1, "image_count": 0}],
    )
    noise = report["extraction_noise"]
    assert noise["unusable_page_count"] == 1
    assert noise["exceeds_threshold"] is True
    assert noise["deterministic"] is True
    request = PdfCorpusBuildCreate(asset_id="pdf-test")
    assert request.noise_unusable_threshold == 45
    assert request.llm_assess_text_noise is False

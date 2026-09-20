from pathlib import Path

from app import autofill as af
from app.enrichment_ledger import (
    ACCEPTED,
    CORRECTED,
    PROPOSED,
    REJECTED,
    EnrichmentLedger,
)


def test_without_history_confidence_is_the_models_own():
    assert af.blended_confidence(0.95, 0, 0) == 0.95


def test_after_prior_reviews_history_and_self_report_count_equally():
    assert af.blended_confidence(1.0, 20, 10) == 0.75  # (10 + 20) / 40


def test_a_run_of_corrections_pulls_a_confident_model_below_the_bar():
    assert af.decide(0.95, 20, 8)["autofill"] is False


def test_autofill_at_the_threshold_and_not_below():
    assert af.decide(0.9, 0, 0)["autofill"] is True
    assert af.decide(0.89, 0, 0)["autofill"] is False
    assert af.decide(None, 0, 0)["autofill"] is False


def test_low_precision_suspends_autofill_only_after_enough_reviews():
    assert af.is_suspended(19, 0) is False
    assert af.is_suspended(20, 15) is True  # 75% < 80%
    assert af.is_suspended(20, 16) is False


def test_suspension_wins_even_when_the_blend_is_high():
    result = af.decide(1.0, 25, 19)  # blend 0.9111, but precision 76%
    assert result["suspended"] is True and result["autofill"] is False


def test_audit_sample_is_stable_and_about_a_tenth():
    picks = [af.in_audit_sample(f"r{i}", "title") for i in range(4000)]
    assert picks == [af.in_audit_sample(f"r{i}", "title") for i in range(4000)]
    assert 0.07 < sum(picks) / len(picks) < 0.13


def test_ledger_counts_reviews_per_model_and_field(tmp_path: Path):
    ledger = EnrichmentLedger(tmp_path / "l.jsonl")
    for kind in (PROPOSED, ACCEPTED, ACCEPTED, CORRECTED, REJECTED):
        ledger.append(kind, model="m", field="title", run_id="r1")
    ledger.append(ACCEPTED, model="other", field="title")
    ledger.append(ACCEPTED, model="m", field="author")
    assert ledger.review_counts("m", "title") == (4, 2)


def test_ledger_survives_a_torn_line(tmp_path: Path):
    ledger = EnrichmentLedger(tmp_path / "l.jsonl")
    ledger.append(ACCEPTED, model="m", field="f")
    with ledger.path.open("a") as handle:
        handle.write('{"kind": "acc')
    assert len(ledger.events()) == 1

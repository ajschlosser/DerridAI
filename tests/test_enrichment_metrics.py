from app.enrichment_metrics import compute
from app.field_assertions import create_model_assertion, project_record_assertions, reopen_assertion


def ev(kind, **kw):
    return {"kind": kind, "model": "m", "field": "f", "build_id": "b", "record_id": "r1", "run_id": "run1", **kw}


def test_acceptance_correction_and_rejection_rates():
    rows = [ev("accepted", confidence=0.9)] * 6 + [ev("corrected", confidence=0.9)] * 3 + [ev("rejected", confidence=0.9)]
    m = compute(rows)["models"]["m"]
    assert (m["acceptance_rate"], m["correction_rate"], m["rejection_rate"]) == (0.6, 0.3, 0.1)


def test_brier_score_penalises_confident_mistakes():
    good = compute([ev("accepted", confidence=1.0)] * 4)["models"]["m"]["brier_score"]
    bad = compute([ev("corrected", confidence=1.0)] * 4)["models"]["m"]["brier_score"]
    assert good == 0.0 and bad == 1.0


def test_precision_and_coverage_by_threshold():
    rows = [ev("proposed", self_reported=0.95)] * 2 + [ev("proposed", self_reported=0.75)] * 2
    rows += [ev("accepted", confidence=0.95), ev("corrected", confidence=0.75)]
    at = {t["threshold"]: t for t in compute(rows)["models"]["m"]["precision_at_threshold"]}
    assert at[0.9]["precision"] == 1.0 and at[0.9]["coverage"] == 0.5
    assert at[0.7]["precision"] == 0.5 and at[0.7]["coverage"] == 1.0


def test_inter_model_agreement():
    rows = [ev("proposed", value="a"), ev("proposed", value="a", model="n"),
            ev("proposed", value="x", record_id="r2"), ev("proposed", value="y", record_id="r2", model="n")]
    assert compute(rows)["inter_model_agreement"] == {"compared": 2, "agreement": 0.5}


def test_stability_across_runs_needs_a_repeat():
    once = [ev("proposed", value="a")]
    assert compute(once)["models"]["m"]["stability"] is None
    twice = once + [ev("proposed", value="a", run_id="run2"), ev("proposed", value="a", record_id="r2"), ev("proposed", value="b", record_id="r2", run_id="run2")]
    assert compute(twice)["models"]["m"]["stability"] == 0.5


def test_grounding_and_cost_per_accepted_field():
    rows = [ev("proposed", grounded=True), ev("proposed", grounded=False), ev("call", elapsed_ms=1000, ok=True),
            ev("call", elapsed_ms=3000, ok=False), ev("accepted", confidence=0.9)]
    m = compute(rows)["models"]["m"]
    assert m["ungrounded_rate"] == 0.5 and m["ms_per_accepted_field"] == 4000 and m["failed_calls"] == 1


def test_learning_curve_uses_whole_buckets_only():
    rows = [ev("corrected", confidence=0.5)] * 10 + [ev("accepted", confidence=0.5)] * 10 + [ev("accepted", confidence=0.5)] * 3
    curve = compute(rows)["models"]["m"]["learning_curve"]
    assert [p["acceptance"] for p in curve] == [0.0, 1.0]


def test_slicing_by_run_and_unresolved_count():
    rows = [ev("accepted", confidence=0.9), ev("corrected", confidence=0.9, run_id="run2")]
    assert compute(rows, run_id="run2")["models"]["m"]["acceptance_rate"] == 0.0
    records = [{"metadata_field_status": {"a": {"status": "unresolved"}, "b": {"status": "model_inferred"}}}]
    assert compute(rows, records)["unresolved_remaining"] == 1




def test_unresolved_metric_uses_assertions_not_flat_status_tokens():
    record = {"record_id": "assertion-metric", "record_revision": 1}
    model = create_model_assertion(record, "stance", "critical", confidence=0.8)
    project_record_assertions(record)
    # Compatibility can be stale or intentionally transformed for an old client.
    record["metadata_field_status"]["stance"]["status"] = "unresolved"
    assert compute([], [record])["unresolved_remaining"] == 0

    reopened = reopen_assertion(record, model, reason="Conflicting later proposal.")
    project_record_assertions(record)
    record["metadata_field_status"]["stance"]["status"] = "model_inferred"
    assert reopened.authority_status == "disputed"
    assert compute([], [record])["unresolved_remaining"] == 1


def test_no_data_is_none_not_zero():
    assert compute([ev("call", elapsed_ms=5, ok=True)])["models"]["m"]["acceptance_rate"] is None


def ts(n):
    return f"2026-01-01T00:00:{n:02d}+00:00"


def test_intervals_accompany_rates():
    rows = [ev("accepted", confidence=0.9)] * 9 + [ev("corrected", confidence=0.9)]
    ci = compute(rows)["models"]["m"]["acceptance_ci"]
    assert ci["n"] == 10 and ci["low"] < 0.9 < ci["high"]


def test_correction_severity_and_substantive_rate():
    rows = [ev("corrected", severity="cosmetic"), ev("corrected", severity="substantive"), ev("accepted"), ev("rejected")]
    m = compute(rows)["models"]["m"]
    assert m["correction_severity"] == {"cosmetic": 1, "substantive": 1, "cleared": 1}
    assert m["substantive_error_rate"]["rate"] == 0.25


def test_repeat_of_a_rejected_value():
    rows = [ev("proposed", value="a", at=ts(1)), ev("corrected", value="a", at=ts(2)),
            ev("proposed", value="a", at=ts(3)), ev("proposed", value="b", at=ts(4))]
    m = compute(rows)["models"]["m"]
    assert m["proposals_after_a_rejection"] == 2 and m["repeat_rate"] == 0.5


def test_text_support_rate_counts_only_free_text_checks():
    rows = [ev("proposed", supported=True), ev("proposed", supported=False), ev("proposed", supported=None)]
    m = compute(rows)["models"]["m"]
    assert m["supported_rate"] == 0.5 and m["supported_checked"] == 2


def test_review_seconds_drops_breaks():
    rows = [ev("accepted", at=ts(0)), ev("accepted", at=ts(10)), ev("accepted", at="2026-01-01T00:20:00+00:00")]
    assert compute(rows)["models"]["m"]["review_seconds_per_decision"] == 10


def test_time_to_first_useful_value_and_suspensions():
    rows = [ev("call", at=ts(0), ok=True, elapsed_ms=1), ev("autofilled", at=ts(12)), ev("suspended", at=ts(20)), ev("resumed", at=ts(30))]
    m = compute(rows)["models"]["m"]
    assert m["seconds_to_first_useful_value"] == 12 and (m["autofill_suspensions"], m["autofill_resumptions"]) == (1, 1)


def test_contested_outcomes_when_models_disagree():
    rows = [ev("proposed", value="a"), ev("proposed", value="b", model="n"),
            ev("corrected", value="a", new_value="b", confidence=0.9)]
    c = compute(rows)["contested"]["m"]
    assert c["contested_reviews"] == 1 and c["person_chose_other_models_value"] == 1


def test_slices_by_arm_and_filter():
    rows = [ev("accepted", arm="A"), ev("corrected", arm="B")]
    out = compute(rows, group_by="arm")
    assert out["slices"]["groups"]["A"]["m"]["acceptance_rate"] == 1.0
    assert compute(rows, arm="B")["models"]["m"]["acceptance_rate"] == 0.0


def test_csv_export_has_condition_columns(tmp_path):
    from app.enrichment_ledger import EnrichmentLedger

    ledger = EnrichmentLedger(tmp_path / "l.jsonl")
    ledger.append("accepted", model="m", field="f", arm="A", ablations=["autofill"], extra_col=1)
    lines = ledger.to_csv().splitlines()
    assert lines[0].startswith("at,kind,run_id") and "extra_col" in lines[0]
    assert '"[""autofill""]"' in lines[1]

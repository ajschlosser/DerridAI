from app.enrichment_metrics import compute


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
    records = [{"metadata_field_status": {"a": {"status": "unresolved"}, "b": {"status": "llm_inferred"}}}]
    assert compute(rows, records)["unresolved_remaining"] == 1


def test_no_data_is_none_not_zero():
    assert compute([ev("call", elapsed_ms=5, ok=True)])["models"]["m"]["acceptance_rate"] is None

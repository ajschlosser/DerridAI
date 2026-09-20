from app.autonomous import Policy, may_accept, settle_record


def rec(**status):
    return {"record_id": "r", "discourse_role": "assertion", "metadata_field_status": status}


def unresolved(conf, value="critique", code="low_confidence"):
    return {"status": "unresolved", "method": "llm", "confidence": conf, "proposed_value": value, "reason_code": code}


def test_policy_reads_and_clamps_the_request():
    p = Policy.from_request({"autonomous": {"enabled": True, "passes": 9, "min_confidence": 0.2, "unresolved": "leave", "publish": True}})
    assert (p.enabled, p.passes, p.min_confidence, p.unresolved, p.publish) == (True, 3, 0.5, "leave", True)
    assert Policy.from_request({}).enabled is False and Policy.from_request(None).enabled is False


def test_a_confident_proposal_is_taken_and_labelled_as_the_models_not_a_persons():
    r = rec(stance=unresolved(0.85))
    out = settle_record(r, Policy(enabled=True, unresolved="leave"))
    assert r["stance"] == "critique" and out["filled"][0]["field"] == "stance"
    info = r["metadata_field_status"]["stance"]
    assert info["status"] == "llm_inferred" and info["method"] == "autonomous_policy" and info["autonomous"] is True
    assert "no person reviewed" in info["reason"]


def test_a_doubtful_proposal_is_left_or_taken_by_policy():
    doubtful = lambda: rec(stance=unresolved(0.5))  # noqa: E731
    left = settle_record(doubtful(), Policy(enabled=True, unresolved="leave"))
    assert left["filled"] == [] and "below 80%" in left["left"][0]["reason"]
    r = doubtful()
    assert settle_record(r, Policy(enabled=True, unresolved="best_guess"))["filled"][0]["field"] == "stance"


def test_a_persons_decision_and_a_field_with_no_proposal_are_never_overridden():
    r = rec(stance={"status": "human_confirmed"}, target={"status": "unresolved", "method": "llm", "reason_code": "ambiguous"})
    out = settle_record(r, Policy(enabled=True))
    assert out["filled"] == [] and out["left"] == [{"field": "target", "reason": "the model proposed no value"}]
    assert r["metadata_field_status"]["stance"]["status"] == "human_confirmed"


def test_a_prefilled_candidate_already_in_the_record_is_kept():
    r = rec(target={"status": "unresolved", "method": "deterministic+llm", "reason_code": "deterministic_llm_disagreement", "confidence": 0.9})
    r["target"] = "cities of refuge"
    assert settle_record(r, Policy(enabled=True))["filled"][0]["value"] == "cities of refuge"


def test_acceptance_needs_nothing_left_waiting():
    assert may_accept({"metadata_review_fields": [], "metadata_incomplete_fields": []}) == (True, [])
    ok, why = may_accept({"metadata_review_fields": ["stance"], "source_quality_issues": [{"x": 1}]})
    assert not ok and any("stance" in w for w in why) and any("source text" in w for w in why)


# ---- through the manager ---------------------------------------------------------------------------------------------

import sys  # noqa: E402
import types  # noqa: E402
from pathlib import Path  # noqa: E402

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb  # noqa: E402
from app.config import APP_VERSION  # noqa: E402


def _setup(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
        "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": APP_VERSION,
        "provider": "ollama", "model": "m", "request": {},
    })
    build.update(status="awaiting_review", stage="review")
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo)
    manager._rewrite_and_validate = lambda bid, records: (repo.save_records(bid, records), repo.get_build(bid))[1]
    return manager, repo, build["build_id"]


def test_hands_free_settles_accepts_and_reports_what_it_could_not(tmp_path):
    m, repo, bid = _setup(tmp_path)
    good = {"record_id": "good", "text": "t", "discourse_role": "assertion", "region_type": "main_text", "primary_text": True,
            "metadata_field_status": {"stance": unresolved(0.9), "discourse_role": {"status": "llm_inferred"}, "region_type": {"status": "deterministic"}, "primary_text": {"status": "deterministic"}}}
    hopeless = {"record_id": "hopeless", "text": "t", "discourse_role": "assertion", "metadata_field_status": {"target": {"status": "unresolved", "method": "llm", "reason_code": "ambiguous"}}}
    touched = {"record_id": "touched", "text": "t", "human_touched_fields": ["stance"], "metadata_field_status": {"stance": unresolved(0.9)}}
    repo.save_records(bid, [good, hopeless, touched])
    report = m.run_autonomous(bid, {"model": "", "autonomous": {"enabled": True, "passes": 0}})
    saved = {r["record_id"]: r for r in repo.load_records(bid)}
    assert saved["good"]["accepted"] is True and saved["good"]["accepted_by"] == "autonomous" and saved["good"]["stance"] == "critique"
    assert saved["good"]["metadata_field_status"]["stance"]["method"] == "autonomous_policy"
    assert saved["hopeless"].get("accepted") is not True and saved["touched"].get("accepted") is not True  # left for a person
    assert report["accepted"] == 1 and report["left_for_review"] == 1 and report["exceptions"][0]["record_id"] == "hopeless"
    assert repo.get_build(bid)["autonomous_report"]["fields_filled"] == 1


def test_hands_free_does_not_publish_unless_asked_and_only_when_nothing_is_left(tmp_path, monkeypatch):
    m, repo, bid = _setup(tmp_path)
    repo.save_records(bid, [{"record_id": "hopeless", "text": "t", "metadata_field_status": {"target": {"status": "unresolved", "method": "llm", "reason_code": "ambiguous"}}}])
    published = []
    monkeypatch.setattr(m, "publish", lambda *a, **k: published.append(1))
    m.run_autonomous(bid, {"autonomous": {"enabled": True, "passes": 0, "publish": True}})
    assert published == []
    assert "Not published" in " ".join(repo.get_build(bid)["autonomous_report"]["notes"])

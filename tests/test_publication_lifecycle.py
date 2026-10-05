# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Publication and review-queue lifecycle.

Why: publishing turns reviewed records into a clean JSONL snapshot without internal
review state, and must be blocked while metadata is incomplete. Build status must
reflect the review/publish stage accurately.
How: `_install_publishable` creates a build with one accepted, complete record
ready to publish; individual tests modify it.
"""

import hashlib
import json
import sys
import types
from pathlib import Path

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb
from app.corpus_segmentation import _apply_manifest_metadata
from app.derridai_ledger import iter_jsonl_zst
from app.field_assertions import create_model_assertion, reset_fields_for_evaluation


def _install_publishable(repo: cb.PdfCorpusRepository):
    """Create an asset, a ready build, and one accepted record that can be published."""
    asset={"asset_id":"pdf-test","sha256":"source-sha","filename":"test.pdf","page_count":1,"block_count":1,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]}
    cb._json_write(repo.asset_meta_path("pdf-test"),asset)
    repo.asset_blocks_path("pdf-test").write_text(json.dumps({"block_id":"b1","page":1,"bbox":[0,0,1,1],"type":"paragraph","text":"Record text","extraction_method":"native","confidence":1.0})+"\n")
    build=repo.create_build({"asset_id":"pdf-test","source_sha256":"source-sha","source_filename":"test.pdf","schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":8,"app_version":"0.60.0","document_prompt_version":cb.DOCUMENT_PROMPT_VERSION,"segmentation_prompt_version":cb.SEGMENTATION_PROMPT_VERSION,"metadata_prompt_version":cb.METADATA_PROMPT_VERSION,"provider":"ollama","model":"profile-model","request":{"provider_profile_id":"primary","record_sizing":{"preferred_record_chars":1750}},"manifest":{"title":"Test Book","document_author":"Test Author"},"validation":{"valid":True}})
    record={"record_id":"r1","record_revision":1,"text":"Record text","text_length":11,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"accepted":True,"review_disposition":"accepted","needs_review":False,"region_type":"main_text","primary_text":True,"discourse_role":"assertion","metadata_complete":True,"metadata_incomplete_fields":[],"metadata_field_status":{"region_type":{"status":"human_confirmed"},"primary_text":{"status":"human_confirmed"},"discourse_role":{"status":"human_confirmed"}}}
    repo.save_records(build["build_id"],[record])
    build.update({"record_count":1,"accepted_count":1,"rejected_count":0,"needs_review_count":0,"validation":{"valid":True},"status":"ready","stage":"ready","progress":.98})
    repo.save_build(build)
    return build

def test_publication_emits_clean_scholarly_records_and_finishes_progress(tmp_path:Path):
    """Publishing writes a public JSONL row without internal fields and completes progress.

    The row keeps record_id and text but drops build details, source block/span/asset
    ids, and review flags. Afterwards status/stage are "ready", publication_status is
    "published", and progress is 1.0.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    publication=manager.publish(build["build_id"])
    path = repo.publication_path(publication["publication_id"])
    integrity = repo.publication_integrity_path(publication["publication_id"])
    assert path.name.endswith(".jsonl.zst")
    assert integrity.read_text(encoding="ascii") == f"{publication['archive_sha512']}  {path.name}\n"
    assert publication["sha512"] == hashlib.sha512(path.read_bytes()).hexdigest()
    assert len(publication["content_sha512"]) == 128
    row = next(iter_jsonl_zst(path, rehydrate_evidence=False))
    assert row["record_id"]=="r1"
    assert row["text"]=="Record text"
    assert "corpus_build_details" not in row
    assert "source_block_ids" not in row and "source_asset_id" not in row
    assert row["source_document_id"] == "pdf-test" and row["source_spans"]
    assert "review_disposition" not in row and "accepted" not in row
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="ready"
    assert refreshed["stage"]=="ready"
    assert refreshed["publication_status"]=="published"
    assert refreshed["progress"]==1.0

def test_publication_keeps_document_level_manifest_metadata(tmp_path:Path):
    """Work/author/etc. inherited from the reviewed document manifest survive to the export.

    These fields are resolved through the FieldAssertion system (like any other
    scholarly field), so the published row must keep their materialized root value
    rather than only the internal assertion bookkeeping: a consumer that opens the
    downloaded JSONL directly, without implementing FieldAssertion resolution, must
    still see the work title and author.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    manifest={"title":"Of Grammatology","document_author":"Jacques Derrida"}
    build["manifest"]=manifest
    repo.save_build(build)
    records=repo.load_records(build["build_id"])
    record=records[0]
    _apply_manifest_metadata(record,manifest)
    repo.save_records(build["build_id"],[record])
    publication=manager.publish(build["build_id"])
    path = repo.publication_path(publication["publication_id"])
    row = next(iter_jsonl_zst(path, rehydrate_evidence=False))
    assert row["work"]=="Of Grammatology"
    assert row["document_title"]=="Of Grammatology"
    assert row["document_author"]=="Jacques Derrida"

def test_review_status_progress_tracks_complete_pipeline(tmp_path:Path):
    """Records still pending review put the build in "awaiting_review" at 90-100% progress."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    records=repo.load_records(build["build_id"])
    records[0].update({"accepted":False,"review_disposition":"pending","needs_review":False})
    manager._rewrite_and_validate(build["build_id"],records)
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="awaiting_review"
    assert refreshed["stage"]=="review"
    assert .90 <= refreshed["progress"] < 1.0


def test_unicode_text_normalization_preserves_foreign_names():
    """Whitespace is trimmed and composed accents are normalized (e + U+0301 -> é), names intact."""
    assert cb._normalize_text("  Édouard   Glissant — différance; Łódź; 東京  ") == "Édouard Glissant — différance; Łódź; 東京"
    assert cb._normalize_text("Cafe\u0301") == "Café"

def test_review_queue_filter_and_bulk_disposition_are_consistent(tmp_path:Path):
    """The "pending" filter and bulk-accept-pending act on the same records."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    records=[
        {"record_id":"r1","record_revision":1,"text":"Édouard Glissant","text_length":15,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"region_type":"main_text","primary_text":True,"discourse_role":"analysis","metadata_field_status":{"region_type":{"status":"deterministic"},"primary_text":{"status":"deterministic"},"discourse_role":{"status":"deterministic"}},"accepted":False,"rejected":False,"review_disposition":"pending","needs_review":False},
        {"record_id":"r2","record_revision":1,"text":"Jacques Derrida","text_length":15,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"region_type":"main_text","primary_text":True,"discourse_role":"analysis","metadata_field_status":{"region_type":{"status":"deterministic"},"primary_text":{"status":"deterministic"},"discourse_role":{"status":"deterministic"}},"accepted":True,"rejected":False,"review_disposition":"accepted","needs_review":False},
    ]
    repo.save_records(build["build_id"],records)
    page=repo.page_records(build["build_id"],disposition="pending")
    assert page["total"]==1 and page["items"][0]["record_id"]=="r1"
    result=manager.bulk_disposition(build["build_id"],"accepted",filter_disposition="pending")
    assert result["changed"]==1
    refreshed=repo.load_records(build["build_id"])
    assert all(row["review_disposition"]=="accepted" for row in refreshed)



def test_metadata_incomplete_creates_explicit_attention_state_and_blocks_publish(tmp_path:Path):
    """An incomplete record keeps the build in review and publishing is refused.

    The refusal message must say metadata is complete for 0 of 1 records.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    build=repo.get_build(build["build_id"])
    rows=repo.load_records(build["build_id"])
    reset_fields_for_evaluation(
        rows[0],
        ["discourse_role"],
        schema=manager._schema_for(build["build_id"]),
        method="publication_incomplete_test",
    )
    manager._rewrite_and_validate(build["build_id"],rows)
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="awaiting_review"
    assert refreshed["stage"]=="review"
    assert refreshed["metadata_issue_summary"]["fields_unresolved"] == 1
    try:
        manager.publish(build["build_id"])
    except ValueError as exc:
        assert "metadata is complete for 0 of 1" in str(exc)
    else:
        raise AssertionError("publication should be blocked by incomplete metadata")

def test_publication_is_snapshot_state_not_build_processing_state(tmp_path:Path):
    """Publishing marks the publication, but the build stays "ready" (not "publishing")."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    manager.publish(build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="ready"
    assert refreshed["stage"]=="ready"
    assert refreshed["publication_status"]=="published"
    assert refreshed["publication"]




def test_new_builds_start_unpublished(tmp_path:Path):
    """A freshly created build has publication_status "unpublished"."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    build=repo.create_build({"asset_id":"a","source_sha256":"s","source_filename":"x.pdf"})
    assert build["publication_status"]=="unpublished"


def test_build_warnings_are_provenance_and_travel_with_the_corpus(tmp_path:Path):
    """A warning about a record is published with that record; the rest with the publication; acknowledgements too.

    Why: warnings such as "r1: LLM text touch-up failed" or "2 of 6 records appear unusable" bear on how far a record
    can be trusted. Dismissing one in the interface records who acknowledged it and when; it is never deleted.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    build["warnings"]=["r1: LLM text touch-up failed; metadata enrichment continued.","2 of 6 records (33.3%) appear unusable."]
    repo.save_build(build)

    acknowledged=manager.acknowledge_warnings(build["build_id"],["2 of 6 records (33.3%) appear unusable."],"aaron")
    assert acknowledged["warnings"]==build["warnings"], "acknowledging never removes a warning"
    try:
        manager.acknowledge_warnings(build["build_id"],["not a warning of this build"],"aaron")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown warning must be refused")

    publication=manager.publish(build["build_id"])
    row=next(iter_jsonl_zst(repo.publication_path(publication["publication_id"]),rehydrate_evidence=False))
    assert [w["text"] for w in row["provenance_warnings"]]==["r1: LLM text touch-up failed; metadata enrichment continued."]
    assert "acknowledged_by" not in row["provenance_warnings"][0]
    [build_wide]=publication["provenance_warnings"]
    assert build_wide["text"].startswith("2 of 6 records")
    assert build_wide["acknowledged_by"]=="aaron" and build_wide["acknowledged_at"]
    assert publication["record_warning_count"]==1
    # The stored record itself is not changed by publishing.
    assert "provenance_warnings" not in repo.load_records(build["build_id"])[0]


def test_accept_unreviewed_publishes_suggestions_and_preserves_prior_decisions(tmp_path:Path):
    """The compatibility path preserves decisions and evaluates cELF independently of review mode.

    r1 was accepted by a reviewer, r2 is still pending with incomplete metadata, r3 was
    rejected. The normal publish is refused; the unreviewed publish succeeds, excludes r3,
    labels r1/r2 by review status, and leaves the stored review state untouched.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    rows=repo.load_records(build["build_id"])
    with repo.asset_blocks_path("pdf-test").open("a") as handle:
        for block in ("b2","b3"):
            handle.write(json.dumps({"block_id":block,"page":1,"bbox":[0,0,1,1],"type":"paragraph","text":"Record text","extraction_method":"native","confidence":1.0})+"\n")
    base={key:value for key,value in rows[0].items() if key!="field_assertions"}
    pending={**base,"record_id":"r2","source_block_ids":["b2"],"source_spans":[{"block_id":"b2","page":1}],"accepted":False,"review_disposition":"pending","needs_review":True}
    rejected={**base,"record_id":"r3","source_block_ids":["b3"],"source_spans":[{"block_id":"b3","page":1}],"accepted":False,"rejected":True,"review_disposition":"rejected"}
    reset_fields_for_evaluation(pending,["discourse_role"],schema=manager._schema_for(build["build_id"]),method="unreviewed_test")
    # Live shape of a pending suggestion: the selected model assertion carries a value but is unresolved.
    suggestion=create_model_assertion(pending,"discourse_role","analysis",schema=manager._schema_for(build["build_id"]),outcome="uncertain",confidence=0.3)
    pending["field_assertions"][suggestion.field_id][-1]["value_status"]="unresolved"
    manager._rewrite_and_validate(build["build_id"],[rows[0],pending,rejected])
    try:
        manager.publish(build["build_id"])
    except ValueError:
        pass
    else:
        raise AssertionError("reviewed publication should still be blocked")
    publication=manager.publish(build["build_id"],accept_unreviewed=True)
    assert publication["review_mode"]=="hybrid"
    assert publication["human_reviewed_record_count"]==1
    assert publication["autonomous_record_count"]==1
    assert publication["celf_conformant"] is True
    assert publication["celf_conformance"]["core"]["blockers"] == []
    assert publication["unreviewed_record_count"]==1
    assert publication["bypassed_review_blocker"]
    assert publication["unreviewed_accepted_field_count"]==1
    rows_out={row["record_id"]:row for row in iter_jsonl_zst(repo.publication_path(publication["publication_id"]),rehydrate_evidence=False)}
    assert set(rows_out)=={"r1","r2"}
    assert rows_out["r1"]["publication_review_status"]=="reviewer_accepted"
    assert rows_out["r2"]["publication_review_status"]=="unreviewed_suggestion"
    assert rows_out["r2"]["needs_review"] is False
    accepted=[
        assertion for bucket in rows_out["r2"]["field_assertions"].values() for assertion in bucket
        if assertion.get("legacy_metadata", {}).get("autonomous_decision")
    ]
    assert [(a["field_name"],a["value"],a["authority_status"],a["value_status"]) for a in accepted]==[("discourse_role","analysis","unreviewed","unresolved")]
    assert not any(
        assertion.get("field_name")=="publication_review_status"
        for bucket in rows_out["r2"].get("field_assertions",{}).values() for assertion in bucket
    )
    stored={row["record_id"]:row for row in repo.load_records(build["build_id"])}
    assert stored["r2"]["review_disposition"]=="pending" and not stored["r2"].get("accepted")
    stored_role=[a for a in stored["r2"]["field_assertions"][suggestion.field_id] if a["assertion_id"]==stored["r2"]["current_field_assertions"][suggestion.field_id]]
    assert stored_role[0]["value_status"]=="unresolved"
    assert stored["r3"]["review_disposition"]=="rejected"


def test_accept_unreviewed_finalizes_sourceunit_topology_before_publication(tmp_path:Path):
    """Autonomous publication accepts current topology without legacy-block false positives."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    build_id=build["build_id"]
    base=repo.load_records(build_id)[0]

    units=repo.load_source_units(build_id)
    units[0]["active"]=False
    template=dict(units[0])
    units.extend([
        {
            **template,
            "source_unit_id":"u-left",
            "unit_id":"u-left",
            "source_block_ids":["b1"],
            "parent_unit_ids":["b1"],
            "consumed_ranges":[{"unit_id":"b1","start":0,"end":6}],
            "text":"Record",
            "active":True,
        },
        {
            **template,
            "source_unit_id":"u-right",
            "unit_id":"u-right",
            "source_block_ids":["b1"],
            "parent_unit_ids":["b1"],
            "consumed_ranges":[{"unit_id":"b1","start":7,"end":11}],
            "text":"text",
            "active":True,
        },
    ])
    repo.save_source_units(build_id,units)

    common={
        **{
            key:value for key,value in base.items()
            if key not in {"field_assertions","current_field_assertions"}
        },
        "accepted":False,
        "rejected":False,
        "review_disposition":"pending",
        "needs_review":True,
        "source_block_ids":["b1"],
        "pdf_pages":[1],
        "page_start":None,
        "page_end":None,
    }
    left={
        **json.loads(json.dumps(common)),
        "record_id":"r-left",
        "text":"Record",
        "text_length":6,
        "source_unit_ids":["u-left"],
        # Reproduces the stale structural projection that used to trigger
        # text_fidelity_errors during publication reconciliation.
        "source_extracted_text":"Record text",
    }
    right={
        **json.loads(json.dumps(common)),
        "record_id":"r-right",
        "text":"text",
        "text_length":4,
        "source_unit_ids":["u-right"],
        "source_extracted_text":"Record text",
    }
    repo.save_records(build_id,[left,right])

    publication=manager.publish(build_id,accept_unreviewed=True)

    assert publication["record_count"]==2
    refreshed=repo.get_build(build_id)
    assert refreshed["validation"]["source_valid"] is True
    assert refreshed["validation"]["duplicate_block_ids"]==[]
    assert refreshed["validation"]["text_fidelity_errors"]==[]
    stored={row["record_id"]:row for row in repo.load_records(build_id)}
    assert stored["r-left"]["source_extracted_text"]=="Record"
    assert stored["r-right"]["source_extracted_text"]=="text"


def test_accept_unreviewed_still_requires_text_fidelity_and_a_finished_build(tmp_path:Path):
    """Bypassing review never bypasses actual source loss or an in-progress build."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    build_id=build["build_id"]

    current=repo.get_build(build_id)
    current["status"]="running"
    repo.save_build(current)
    try:
        manager.publish(build_id,accept_unreviewed=True)
    except ValueError as exc:
        assert "finished processing" in str(exc)
    else:
        raise AssertionError("an active build must not publish")

    current=repo.get_build(build_id)
    current.update({"status":"ready","stage":"ready","validation":{"valid":True}})
    repo.save_build(current)
    rows=repo.load_records(build_id)
    rows[0]["source_block_ids"]=[]
    rows[0]["source_unit_ids"]=[]
    repo.save_records(build_id,rows)
    try:
        manager.publish(build_id,accept_unreviewed=True)
    except ValueError as exc:
        assert "text-fidelity" in str(exc)
    else:
        raise AssertionError("actual missing source coverage must still block publication")


def test_accept_unreviewed_repairs_retired_sourceunit_binding_before_publication(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    build_id=build["build_id"]
    rows=repo.load_records(build_id)

    units=repo.load_source_units(build_id)
    units[0]["active"]=False
    old=dict(units[0])
    old["source_unit_id"]="u-old"
    old["unit_id"]="u-old"
    old["text"]="Record text"
    old["active"]=False
    units.append(old)
    units.extend([
        {
            **old,
            "source_unit_id":"u-left",
            "unit_id":"u-left",
            "parent_unit_ids":["u-old"],
            "text":"Record",
            "active":True,
        },
        {
            **old,
            "source_unit_id":"u-right",
            "unit_id":"u-right",
            "parent_unit_ids":["u-old"],
            "text":"text",
            "active":True,
        },
    ])
    repo.save_source_units(build_id,units)

    rows[0]["source_unit_ids"]=["u-old"]
    rows[0]["source_block_ids"]=["b1"]
    rows[0]["source_extracted_text"]="Record text"
    rows[0]["accepted"]=False
    rows[0]["review_disposition"]="pending"
    rows[0]["needs_review"]=True
    repo.save_records(build_id,rows)

    publication=manager.publish(build_id,accept_unreviewed=True)

    assert publication["record_count"]==1
    stored=repo.load_records(build_id)[0]
    assert stored["source_unit_ids"]==["u-left","u-right"]
    assert stored["source_extracted_text"]=="Record\n\ntext"
    history=stored["source_topology_reconciliation_history"]
    assert history[-1]["previous_source_unit_ids"]==["u-old"]
    assert history[-1]["source_text_conserved"] is True
    refreshed=repo.get_build(build_id)
    assert refreshed["validation"]["source_valid"] is True
    assert refreshed["source_topology_reconciliation_history"]


def test_publication_blocker_names_remaining_source_findings():
    from app.corpus_publication import publication_blocker

    validation = {
        "source_valid": False,
        "valid": False,
        "missing_source_unit_ids": ["u-missing"],
        "validation_issues": [
            {
                "code": "source_coverage",
                "record_id": "",
                "field": "u-missing",
                "reason": "active source unit is not covered by any Record",
            }
        ],
    }
    message = publication_blocker(
        {"status": "awaiting_review"},
        [{"record_id": "r1"}],
        validation,
        require_acceptance=False,
        accept_unreviewed=True,
    )

    assert message is not None
    assert "source_coverage: 1" in message
    assert "u-missing" in message
    assert "active source unit is not covered" in message


def test_accept_unreviewed_on_a_fully_reviewed_build_stays_conformant(tmp_path:Path):
    """If nothing was actually bypassed, the publication remains cELF-conformant."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    publication=manager.publish(build["build_id"],accept_unreviewed=True)
    assert publication["celf_conformant"] is True and publication["unreviewed_record_count"]==0

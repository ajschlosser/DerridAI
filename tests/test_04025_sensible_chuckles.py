"""Publication and review-queue lifecycle (release 0.40.25, "Sensible Chuckles").

Why: publishing turns reviewed records into a clean JSONL snapshot without internal
review state, and must be blocked while metadata is incomplete. Build status must
reflect the review/publish stage accurately.
How: `_install_publishable` creates a build with one accepted, complete record
ready to publish; individual tests modify it.
"""

from pathlib import Path
import json
import sys, types
sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb

def text(path):
    """Read a repository file as UTF-8 text.

    Currently unused in this file: it is a leftover from earlier source-text checks that were
    removed (AGENTS.md: test behavior, not text). Safe to delete in a code-changing cleanup.
    """
    return (ROOT/path).read_text(encoding="utf-8")




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
    row=json.loads(repo.publication_path(publication["publication_id"]).read_text().splitlines()[0])
    assert row["record_id"]=="r1"
    assert row["text"]=="Record text"
    assert "corpus_build_details" not in row
    assert "source_block_ids" not in row and "source_spans" not in row and "source_asset_id" not in row
    assert "review_disposition" not in row and "accepted" not in row
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="ready"
    assert refreshed["stage"]=="ready"
    assert refreshed["publication_status"]=="published"
    assert refreshed["progress"]==1.0

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
    rows[0]["metadata_complete"]=False
    rows[0]["metadata_incomplete_fields"]=["discourse_role"]
    rows[0].pop("discourse_role",None)
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

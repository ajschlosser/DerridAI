"""Text cleanup and publication-readiness rules.

Why: extracted PDF text needs conservative cleanup without damaging verse, and the
publish gate must treat rejected records correctly.
How: calls the pure cleanup function and the workflow-refresh helper on dicts.
"""

import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb'] = types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb


def test_cleanup_repairs_multi_line_prose_and_ocr_without_flattening_poetry():
    """Rejoin wrapped prose and fix ligatures, but leave short-line verse alone.

    What: hard-wrapped prose becomes one line, the "fi" ligature is normalized, and the
    paragraph break is kept. A four-line quoted verse passes through unchanged.
    Why: flattening poetry would alter the quoted text and its meaning; cleanup is
    deliberately conservative (see AGENTS.md on preprocessing).
    """
    prose='This sentence is artificially wrapped across\nseveral physical PDF lines in the middle\nof one continuous thought and contains ﬁ ligature.\n\nNext paragraph.'
    cleaned,report=cb._clean_text_value(prose,{'paragraph_lines','ocr_artifacts','empty_lines'},set())
    assert 'wrapped across several physical PDF lines in the middle of one continuous thought' in cleaned
    assert 'fi ligature' in cleaned
    assert '\n\nNext paragraph.' in cleaned
    assert report['changed'] is True
    verse='“First short line\nSecond short line\nThird short line\nFourth short line”'
    verse_cleaned,_=cb._clean_text_value(verse,{'paragraph_lines'},set())
    assert verse_cleaned==verse

def test_rejected_records_are_not_publication_metadata_blockers_and_all_rejected_is_terminal():
    """Rejected records do not block publishing; rejecting everything ends the workflow.

    What: with 2 accepted and 1 rejected record, can_publish is True and there is no
    "rejected_records" blocker. With all 3 rejected, publication_readiness reports
    no_publishable_records and that as the next action.
    Why: rejected records are excluded from publication, so they must not hold up the
    build, but a build with nothing to publish must not appear publishable.
    """
    build={'record_count':3,'accepted_count':2,'rejected_count':1,'needs_review_count':0,'boundary_review_count':0,'source_problem_count':0,'metadata_total':3,'metadata_completed':3,'metadata_issue_summary':{'records_incomplete':0,'fields_unresolved':0},'manifest':{'title':'Book','document_author':'Author'},'validation':{'valid':True,'source_valid':True,'metadata_valid':True},'status':'awaiting_review','stage':'review'}
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build['publication_readiness']['can_publish'] is True
    assert not any(row['code']=='rejected_records' for row in build['publication_readiness']['blockers'])
    build.update({'accepted_count':0,'rejected_count':3})
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    assert build['publication_readiness']['no_publishable_records'] is True
    assert build['publication_readiness']['next_action']=='no_publishable_records'










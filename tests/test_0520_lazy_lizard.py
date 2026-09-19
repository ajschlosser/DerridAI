"""Automatic text cleanup, publication gate, and adaptive enrichment (release 0.52.0, "Lazy Lizard").

Why: extracted PDF text carries running headers, page numbers and layout line
breaks that would pollute records and prompts, but the untouched source text must
remain recoverable. The publish gate must know a book's identity, and fast
enrichment may skip families that are not paying off (never when explicitly asked).
How: pure helpers and PdfCorpusBuildManager methods called with small dicts.
"""

from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb'] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'api'))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_pre_enrichment_cleanup_is_default_and_preserves_source_truth():
    """Cleanup is on by default, removes noise, and keeps the original and a diff.

    What: two records contain a repeated running title, a page number, a "Downloaded
    from JSTOR" line and a sentence broken by layout. After cleanup both records are
    changed; the header, page number and boilerplate are gone; the broken clause is
    rejoined; the untouched text is kept in source_extracted_text; and
    text_revision_history logs an "automatic_cleanup" entry with a diff.
    Why: cleanup improves prompts, but provenance requires the original text.
    """
    request = PdfCorpusBuildCreate(asset_id='pdf-test')
    assert request.auto_clean_text is True
    assert 'ocr_artifacts' in request.text_cleanup_rules
    records = [
        {
            'record_id': 'r1',
            'text': 'ON COSMOPOLITANISM\n12\nThis sentence was broken in the middle of\na clause by PDF layout.\nDownloaded from JSTOR.org\nON COSMOPOLITANISM',
            'text_length': 142,
        },
        {
            'record_id': 'r2',
            'text': 'ON COSMOPOLITANISM\n13\nAnother sentence continues over\na layout line without punctuation.\nON COSMOPOLITANISM',
            'text_length': 120,
        },
    ]
    report = cb.apply_automatic_text_cleanup(
        records,
        request.text_cleanup_rules,
        document_terms=['On Cosmopolitanism'],
    )
    assert report['records_changed'] == 2
    assert records[0]['source_extracted_text'].startswith('ON COSMOPOLITANISM')
    assert 'ON COSMOPOLITANISM' not in records[0]['text']
    assert '\n12\n' not in records[0]['text']
    assert 'Downloaded from JSTOR.org' not in records[0]['text']
    assert 'middle of a clause' in records[0]['text']
    assert records[0]['text_revision_history'][-1]['source'] == 'automatic_cleanup'
    assert records[0]['text_revision_history'][-1]['diff']


def test_cleanup_preserves_likely_poetry_and_quotation_layout():
    """Short quoted verse lines are not joined into prose.

    Why: rejoining verse changes the quotation. The report must say nothing changed.
    """
    poetry = '“First short line\nSecond short line\nThird short line\nFourth short line”'
    cleaned, report = cb._clean_text_value(poetry, {'paragraph_lines'}, set())
    assert cleaned == poetry
    assert report['changed'] is False


def test_publication_readiness_requires_document_identity_and_semantic_integrity():
    """A build with no title or author cannot be published.

    What: otherwise-complete accepted metadata but an empty manifest title and author.
    Expect can_publish False, both fields listed as missing, and a
    required_document_metadata blocker.
    Why: citations are built from document title/author.
    """
    build = {
        'profile_id': cb.PROFILE_VERSION,
        'record_count': 1,
        'accepted_count': 1,
        'rejected_count': 0,
        'needs_review_count': 0,
        'boundary_review_count': 0,
        'source_problem_count': 0,
        'metadata_total': 1,
        'metadata_completed': 1,
        'metadata_issue_summary': {'fields_unresolved': 0, 'records_incomplete': 0},
        'manifest': {'title': '', 'document_author': ''},
        'validation': {'valid': True, 'source_valid': True, 'metadata_valid': True},
        'status': 'ready',
        'stage': 'ready',
    }
    cb.PdfCorpusBuildManager._refresh_workflow_fields(build)
    readiness = build['publication_readiness']
    assert readiness['can_publish'] is False
    assert set(readiness['missing_document_fields']) == {'title', 'document_author'}
    assert any(item['code'] == 'required_document_metadata' for item in readiness['blockers'])


def test_adaptive_fast_mode_can_skip_repeatedly_low_yield_family_but_not_deep_or_explicit_rerun():
    """Fast mode skips a family that keeps proposing almost nothing; other modes never do.

    Setup: 7 indexing calls have proposed only 1 field. Fast mode should skip the
    family (with a reason). Deep mode, and a fast run that explicitly names the
    "indexing" family, must still run it.
    Why: a reviewer who asks for a family must always get it.
    """
    class Repo:
        def get_build(self, _build_id):
            return {'llm_family_effectiveness': {'indexing': {'calls': 7, 'proposed_fields': 1}}}
    manager = object.__new__(cb.PdfCorpusBuildManager)
    manager.repo = Repo()
    skip, reason = manager._adaptive_family_should_skip('b1', 'indexing', {'enrichment_mode': 'fast'})
    assert skip is True and reason
    assert manager._adaptive_family_should_skip('b1', 'indexing', {'enrichment_mode': 'deep'})[0] is False
    assert manager._adaptive_family_should_skip('b1', 'indexing', {'enrichment_mode': 'fast', 'families': ['indexing']})[0] is False









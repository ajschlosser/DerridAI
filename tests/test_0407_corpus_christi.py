"""Semantic-atom reconstruction and MLA citation formatting (release 0.40.7, "Corpus Christi").

Why: PDF text arrives as visual lines, not sentences. Segmentation needs
sentence-like "atoms" whose anchors are real block IDs, and published records need
correct MLA citations built by deterministic code (never by the LLM).
How: calls the pure helpers on small hand-written blocks and citation dicts.
"""

from __future__ import annotations

from pathlib import Path

from app import corpus_builder as cb
from app.bibliography import _mla_citation

ROOT = Path(__file__).resolve().parents[1]

def text(path: str) -> str:
    """Read a repository file as UTF-8 text.

    Currently unused in this file: it is a leftover from earlier source-text checks that were
    removed (AGENTS.md: test behavior, not text). Safe to delete in a code-changing cleanup.
    """
    return (ROOT / path).read_text(encoding="utf-8")




def test_semantic_atom_reconstruction_preserves_real_boundary_anchor():
    """Merged visual lines still anchor to a real source block.

    What: b1 ("A short visual line") has no terminal punctuation and b2 continues the
    sentence, so they merge into one atom; b3 starts a new paragraph.
    Checks: the first atom's block_id is a real block (b2 or b3, never an invented id)
    and its source_block_ids still begin with b1, so provenance back to the PDF is kept.
    """
    blocks = [
        {"block_id":"b1","page":1,"type":"body","text":"A short visual line", "bbox":[0,0,1,1]},
        {"block_id":"b2","page":1,"type":"body","text":"continues the same sentence.", "bbox":[0,1,1,2]},
        {"block_id":"b3","page":1,"type":"body","text":"A new paragraph begins here and completes its thought.", "bbox":[0,3,1,4]},
    ]
    atoms = cb.PdfCorpusBuildManager._semantic_atoms(blocks)
    assert atoms
    assert atoms[0]["block_id"] in {"b2", "b3"}
    assert atoms[0]["source_block_ids"][0] == "b1"


def test_mla_supports_books_journal_articles_and_chapters():
    """MLA citations include the fields each source type requires.

    What: a book (title, publisher), a journal article (journal, vol., no., pp., DOI
    inputs) and a book chapter (container title, "edited by", pp.).
    Why: citations are produced deterministically from metadata, so a missing
    volume/issue/editor here would produce a wrong scholarly citation.
    """
    book = _mla_citation({"source_type":"book","document_author":"Jacques Derrida","document_title":"Archive Fever","publisher":"University of Chicago Press","publication_year":1996})
    article = _mla_citation({"source_type":"journal_article","document_author":"Jane Doe","document_title":"An Article","journal_title":"Critical Inquiry","volume":"15","issue":"4","publication_year":1989,"pages":"812-873","doi":"10.1234/example"})
    chapter = _mla_citation({"source_type":"book_chapter","document_author":"Jane Doe","document_title":"A Chapter","container_title":"Collected Essays","editor":"John Smith","publisher":"Example Press","publication_year":2026,"pages":"10-25"})
    assert "Archive Fever" in book and "University of Chicago Press" in book
    assert "Critical Inquiry" in article and "vol. 15" in article and "no. 4" in article and "pp. 812-873" in article
    assert "Collected Essays" in chapter and "edited by John Smith" in chapter and "pp. 10-25" in chapter








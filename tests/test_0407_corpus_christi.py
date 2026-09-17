from __future__ import annotations

import json
from pathlib import Path

from app import corpus_builder as cb
from app.bibliography import _mla_citation

ROOT = Path(__file__).resolve().parents[1]

def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0408_release_identity():
    assert json.loads(text("web/package.json"))["version"] == "0.40.15"
    assert 'APP_VERSION = "0.40.15"' in text("api/app/config.py")
    assert "0.40.15 — The Record Scratch Moment" in text("README.md")


def test_segmentation_uses_deterministic_candidates_and_boundary_level_review():
    builder = text("api/app/corpus_builder.py")
    assert "def _semantic_atoms" in builder
    assert "def _manifest_main_text_blocks" in builder
    assert "def _deterministic_boundary_candidates" in builder
    assert "local_batch_classifier" in builder
    assert "omission/failure/low confidence also means KEEP" in builder
    assert '"segmentation_boundary_reviews":boundary_reviews[:500]' in builder
    assert "boundary_review_after" in builder and "boundary_review_before" in builder


def test_semantic_atom_reconstruction_preserves_real_boundary_anchor():
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
    book = _mla_citation({"source_type":"book","document_author":"Jacques Derrida","document_title":"Archive Fever","publisher":"University of Chicago Press","publication_year":1996})
    article = _mla_citation({"source_type":"journal_article","document_author":"Jane Doe","document_title":"An Article","journal_title":"Critical Inquiry","volume":"15","issue":"4","publication_year":1989,"pages":"812-873","doi":"10.1234/example"})
    chapter = _mla_citation({"source_type":"book_chapter","document_author":"Jane Doe","document_title":"A Chapter","container_title":"Collected Essays","editor":"John Smith","publisher":"Example Press","publication_year":2026,"pages":"10-25"})
    assert "Archive Fever" in book and "University of Chicago Press" in book
    assert "Critical Inquiry" in article and "vol. 15" in article and "no. 4" in article and "pp. 812-873" in article
    assert "Collected Essays" in chapter and "edited by John Smith" in chapter and "pp. 10-25" in chapter


def test_work_metadata_tries_multiple_catalogues_and_exposes_container_fields():
    llm = text("api/app/llm_tools.py")
    runtime = text("web/src/legacy/runtime.js")
    assert "def _crossref_candidates" in llm
    assert "def _google_books_candidates" in llm
    assert "def _multi_catalog_candidates" in llm
    assert "Open Library" in llm and "Google Books" in llm and "Crossref" in llm
    assert '"source_type", "document_type", "document_title"' in llm
    assert '"container_title", "journal_title", "editor", "edition"' in llm
    assert '"isbn", "doi", "url", "full_citation", "cover_url"' in llm
    assert "catalog_sources_tried" in llm
    for field in ("source_type","container_title","journal_title","volume","issue","pages","doi"):
        assert field in runtime


def test_work_separation_and_saved_subset_profiles_are_first_class_ui_flows():
    runtime = text("web/src/legacy/runtime.js")
    style = text("web/src/style.css")
    assert "function openSeparateWorksModal" in runtime
    assert 'id="separateWorks"' in runtime
    assert "SUBSET_PROFILE_STORAGE_KEY" in runtime
    assert "loadSubsetProfiles" in runtime and "saveSubsetProfiles" in runtime
    assert 'id="saveSubsetProfile"' in runtime and 'id="deleteSubsetProfile"' in runtime
    assert ".subset-config-card" in style and ".separate-works-list" in style

def test_pdf_corpus_builder_review_action_calls_declared_refresh_handler():
    builder = text("web/src/components/PdfCorpusBuilder.vue")
    assert 'loadRecords()' not in builder



def test_corpus_build_progress_does_not_dereference_nullable_validation_in_template():
    progress = text("web/src/components/CorpusBuildProgress.vue")
    template = progress.split("<template>", 1)[1].split("</template>", 1)[0]
    assert "props.validation." not in template
    assert "validationCoverage" in progress
    assert "validationSchemaIssues" in progress

from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def text(p): return (ROOT/p).read_text(encoding="utf-8")
def test_release_version():
    assert json.loads(text("web/package.json"))["version"]=="0.42.0"
    assert 'version="0.42.0"' in text("api/app/main.py")
    assert 'APP_VERSION = "0.42.0"' in text("api/app/config.py")
    assert "0.42.0 — Bunny Rabbit" in text("README.md")
def test_review_workflow_contract():
    c=text("api/app/corpus_builder.py")
    assert "def set_disposition" in c and "def bulk_disposition" in c and "def undo_last_review_edit" in c
    assert 'review_disposition' in c and 'review_undo' in c
    assert 'Keep the first record' in c and 'Preserved across human split' in c
def test_focus_and_pdf_lifecycle():
    assert (ROOT/"web/src/components/CorpusRecordFocusReview.vue").exists()
    assert (ROOT/"web/src/components/CorpusRecordFocusReview.stories.ts").exists()
    v=text("web/src/components/PdfEvidenceViewer.vue")
    assert "async function destroyDocument" in v and "await task.destroy?.()" in v
    assert "watch(()=>props.pdfUrl" in v and "watch(()=>props.page" in v
def test_review_ui_has_bulk_reject_undo_and_focus():
    v=text("web/src/components/PdfCorpusBuilder.vue")
    for token in ["bulkDisposition","rejectRecord","undoReview","focusView","canMergePrevious","accepted_notice"]: assert token in v

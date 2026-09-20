from app.main_text_start import infer_main_text_start as infer


def doc(page_specs, labels=None):
    blocks, pages = [], []
    for n, lines in enumerate(page_specs, 1):
        for j, t in enumerate(lines):
            blocks.append({"block_id": f"p{n}b{j}", "page": n, "text": t, "type": "body"})
        pages.append({"pdf_page": n, "printed_page_label": (labels or {}).get(n)})
    return blocks, pages


BOOK = [
    ["Title Page"],
    ["Contents", "Preface .... vii", "Chapter One .... 1", "Chapter Two .... 40", "Notes .... 90"],
    ["Preface", "This book grew out of lectures given over many years."],
    ["More thanks to the many people who helped."],
    ["Chapter One", "The argument begins here and continues for a while."],
    ["Text of the chapter goes on and on."],
]
LABELS = {2: "v", 3: "vi", 4: "vii", 5: "1", 6: "2"}


def test_agreeing_clues_offer_the_page_with_reasons():
    b, p = doc(BOOK, LABELS)
    result = infer(b, p, [(5, "Chapter One")])
    assert result["page"] == 5 and result["offered"] is True
    kinds = {c["kind"] for c in result["clues"]}
    assert {"outline_first_chapter", "first_chapter_heading"} <= kinds


def test_contents_listing_is_not_mistaken_for_the_heading():
    b, p = doc(BOOK, LABELS)
    assert infer(b, p, [])["page"] == 5


def test_one_weak_clue_is_not_offered():
    b, p = doc([["Front"], ["Body text here."], ["More."]], {2: "1"})
    result = infer(b, p, [])
    assert not result["offered"]


def test_introduction_is_not_a_start_marker():
    b, p = doc([["Title"], ["Introduction", "Some words."], ["Chapter One", "Words."]])
    assert infer(b, p, [(2, "Introduction")])["page"] == 3


def test_conflicting_evidence_lowers_confidence():
    b, p = doc(BOOK, LABELS)
    agree = infer(b, p, [(5, "Chapter One")])["confidence"]
    disagree = infer(b, p, [(3, "Chapter 1")])
    assert disagree["confidence"] < agree


def test_nothing_found_offers_nothing():
    b, p = doc([["Just prose."], ["More prose."]])
    assert infer(b, p, []) == {"page": None, "confidence": 0.0, "clues": [], "offered": False}


def test_extraction_records_the_outline_and_inference(tmp_path):
    import fitz
    from app.corpus_builder import extract_source_document

    pdf = fitz.open()
    for text in ("Title", "Preface\nThanks to everyone.", "Chapter One\nThe argument begins."):
        pdf.new_page().insert_text((72, 100), text)
    pdf.set_toc([[1, "Chapter One", 3]])
    result = extract_source_document(pdf.tobytes(), filename="b.pdf")
    assert result["outline"] == [{"page": 3, "title": "Chapter One"}]
    assert result["main_text_start_inference"]["page"] == 3


def test_numbered_first_chapter_headings_count():
    b, p = doc([["Title"], ["Contents", "1 Beginnings .... 3"], ["1. Beginnings", "It starts here and goes on."]])
    assert infer(b, p, [])["page"] == 3
    b, p = doc([["Title"], ["I think this matters."], ["I. The Question", "Words follow."]])
    result = infer(b, p, [])
    assert result["page"] == 3 and len(result["clues"]) == 1  # "I think" is not a heading


def test_bookmarks_after_the_front_matter_agree_with_a_numbering_restart():
    b, p = doc([["Title"], ["Words"], ["Words"], ["Words"], ["Words"], ["Words"]], {2: "i", 3: "ii", 4: "1"})
    outline = [(2, "Contents"), (3, "Preface"), (3, "Introduction"), (4, "The Argument")]
    result = infer(b, p, outline)
    kinds = {c["kind"] for c in result["clues"]}
    assert result["page"] == 4 and {"outline_after_front_matter", "page_numbering_restarts"} <= kinds


def test_an_older_asset_gets_the_inference_when_first_read(tmp_path):
    import json

    from app import corpus_builder as cb

    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    blocks = [{"block_id": f"b{i}", "page": p, "text": t, "type": "body"} for i, (p, t) in enumerate([(1, "Title"), (2, "Preface"), (3, "Chapter One"), (3, "The argument begins here.")])]
    (repo.root / "assets" / "pdf-old.blocks.jsonl").write_text("\n".join(json.dumps(b) for b in blocks))
    meta = {"asset_id": "pdf-old", "filename": "o.pdf", "pages": [{"pdf_page": n, "printed_page_label": None} for n in (1, 2, 3)]}
    (repo.root / "assets" / "pdf-old.json").write_text(json.dumps(meta))
    first = repo.get_asset("pdf-old")
    assert first["main_text_start_inference"]["page"] == 3
    assert "main_text_start_inference" in json.loads((repo.root / "assets" / "pdf-old.json").read_text())  # kept

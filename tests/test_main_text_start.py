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

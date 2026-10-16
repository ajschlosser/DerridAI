# Copyright 2026 Aaron John Schlosser, PhD.
"""MLA 9 citations in Research: Works Cited entries and in-text forms come from
recorded Record metadata by deterministic code, never from the model."""
from __future__ import annotations

from app.corpus_citations import mla_in_text, mla_works_cited, mla_works_cited_entry
from app.rag import _annotate_mla, _bind_sources
from app.research_thread_export import build_thread_export

GRAMMATOLOGIE = {
    "record_id": "r1", "canonical_work_id": "w-gram", "work": "De la grammatologie",
    "document_author": "Jacques Derrida", "publisher": "Éditions de Minuit",
    "edition": "Éditions de Minuit", "year": 1965, "page_start": 23, "page_end": 25,
}
DISSEMINATION = {
    "record_id": "r2", "canonical_work_id": "w-diss", "work": "Dissemination",
    "document_author": "Jacques Derrida", "translator": "Barbara Johnson",
    "publisher": "U of Chicago P", "year": 1981, "page_start": 95,
}
NIETZSCHE = {
    "record_id": "r3", "canonical_work_id": "w-nietzsche", "work": "Nietzsche",
    "document_author": "Martin Heidegger", "translator": "Joan Stambaugh",
    "publisher": "Harper & Row", "year": 1982, "page_start": 397, "page_end": 398,
}


def _evidence(*records: dict) -> list[dict]:
    return [
        {"evidence_id": f"E{index}", "inline_citation": f"Cite {index}", "full_citation": f"Full {index}",
         "record": record}
        for index, record in enumerate(records)
    ]


def test_works_cited_entry_italicizes_the_title_and_keeps_the_recorded_year() -> None:
    # The recorded year is wrong (1967); formatting must not correct or hide it.
    assert mla_works_cited_entry(GRAMMATOLOGIE) == (
        "Derrida, Jacques. *De la grammatologie*. Éditions de Minuit, 1965."
    )
    assert mla_works_cited_entry(DISSEMINATION) == (
        "Derrida, Jacques. *Dissemination*. Translated by Barbara Johnson, U of Chicago P, 1981."
    )


def test_works_cited_is_alphabetical_one_per_work_with_hyphens_for_a_repeated_author() -> None:
    second_passage = {**GRAMMATOLOGIE, "record_id": "r9", "page_start": 61, "page_end": None}
    entries = mla_works_cited([NIETZSCHE, DISSEMINATION, GRAMMATOLOGIE, second_passage])
    assert entries == [
        "Derrida, Jacques. *De la grammatologie*. Éditions de Minuit, 1965.",
        "---. *Dissemination*. Translated by Barbara Johnson, U of Chicago P, 1981.",
        "Heidegger, Martin. *Nietzsche*. Translated by Joan Stambaugh, Harper & Row, 1982.",
    ]


def test_in_text_uses_author_and_pages_and_adds_the_title_only_when_needed() -> None:
    assert mla_in_text(NIETZSCHE, include_title=False) == "(Heidegger 397–398)"
    assert mla_in_text(GRAMMATOLOGIE, include_title=True) == "(Derrida, *De la grammatologie* 23–25)"
    assert mla_in_text({"work": "Anonymous Tract", "page_start": 4}, include_title=False) == (
        "(*Anonymous Tract* 4)"
    )
    assert mla_in_text({"record_id": "bare"}, include_title=False) == ""


def test_bound_answer_ends_with_an_unnumbered_alphabetical_mla_works_cited() -> None:
    evidence = _evidence(NIETZSCHE, GRAMMATOLOGIE, DISSEMINATION)
    answer = _bind_sources("Presence [[E1]] and the pharmakon [[E2]], read by Heidegger [[E0]].", evidence, True)
    body, works = answer.split("**Works Cited**")
    assert "(Cite 1)" in body and "(Cite 2)" in body
    assert works.strip().splitlines() == [
        "Derrida, Jacques. *De la grammatologie*. Éditions de Minuit, 1965.",
        "---. *Dissemination*. Translated by Barbara Johnson, U of Chicago P, 1981.",
        "Heidegger, Martin. *Nietzsche*. Translated by Joan Stambaugh, Harper & Row, 1982.",
    ]


def test_uncited_evidence_is_not_listed_in_works_cited() -> None:
    evidence = _evidence(GRAMMATOLOGIE, NIETZSCHE)
    answer = _bind_sources("Only Derrida [[E0]].", evidence, True)
    assert "Heidegger" not in answer


def test_annotation_disambiguates_an_author_with_several_cited_works() -> None:
    evidence = _evidence(GRAMMATOLOGIE, DISSEMINATION, NIETZSCHE)
    _annotate_mla(evidence, "A [[E0]] B [[E1]] C [[E2]]")
    assert [item["mla_in_text"] for item in evidence] == [
        "(Derrida, *De la grammatologie* 23–25)",
        "(Derrida, *Dissemination* 95)",
        "(Heidegger 397–398)",
    ]
    only_one = _evidence(GRAMMATOLOGIE, DISSEMINATION)
    _annotate_mla(only_one, "A [[E0]]")
    assert only_one[0]["mla_in_text"] == "(Derrida 23–25)"
    assert only_one[1]["mla_citation"].startswith("Derrida, Jacques. *Dissemination*.")


def test_thread_export_uses_mla_in_text_and_one_alphabetical_works_cited() -> None:
    results = {
        "j1": {"answer": "old", "raw_answer": "Heidegger [[E0]] reads presence [[E1]].",
               "evidence": _evidence(NIETZSCHE, GRAMMATOLOGIE)},
        "j2": {"answer": "old", "raw_answer": "The pharmakon [[E0]].", "evidence": _evidence(DISSEMINATION)},
    }
    thread = {"thread_id": "t", "title": "T", "turns": [
        {"turn_id": f"u{index}", "ordinal": index, "attempt": 1, "status": "completed",
         "user_question": "Q", "job_id": job}
        for index, job in enumerate(results, start=1)
    ]}
    export = build_thread_export(thread, lambda turn: {"result": results[turn["job_id"]]})
    first, second = export["turns"]
    assert first["answer"] == "Heidegger (Heidegger 397–398) reads presence (Derrida 23–25)."
    assert second["answer"] == "The pharmakon (Derrida 95)."
    assert "Works Cited" not in first["answer"]
    assert export["works_cited"] == [
        "Derrida, Jacques. *De la grammatologie*. Éditions de Minuit, 1965.",
        "---. *Dissemination*. Translated by Barbara Johnson, U of Chicago P, 1981.",
        "Heidegger, Martin. *Nietzsche*. Translated by Joan Stambaugh, Harper & Row, 1982.",
    ]

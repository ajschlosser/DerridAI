# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic POS/NER candidates: exact spans, hints only, stale when the text changes."""

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import nlp_annotations as nlp  # noqa: E402


class Ent:
    def __init__(self, text, label, start):
        self.text, self.label_, self.start_char, self.end_char = text, label, start, start + len(text)


class Tok:
    def __init__(self, text, pos, idx, *, is_stop=False):
        self.text, self.pos_, self.idx, self.is_stop = text, pos, idx, is_stop


def _doc(text):
    ents = [Ent("Rousseau", "PER", text.index("Rousseau")), Ent("Geneva", "GPE", text.index("Geneva"))]
    toks, cursor = [], 0
    for word in text.split(" "):
        toks.append(Tok(word, "PROPN" if word[0].isupper() else "VERB", cursor))
        cursor += len(word) + 1
    return NS(ents=ents, __iter__=None), toks


class FakeDoc:
    def __init__(self, text):
        self.ents, self._toks = _doc(text)[0].ents, _doc(text)[1]

    def __iter__(self):
        return iter(self._toks)


TEXT = "Rousseau left Geneva quietly"
SCHEMA = NS(fields=[
    NS(name="position_holder", pos_tags=[], ner_tags=["PERSON"]),
    NS(name="place", pos_tags=[], ner_tags=["LOC"]),
    NS(name="terms", pos_tags=["PROPN"], ner_tags=[]),
    NS(name="plain", pos_tags=[], ner_tags=[]),
])


@pytest.fixture()
def fake_pipeline(monkeypatch):
    monkeypatch.setattr(nlp, "load_pipeline", lambda language: (lambda text: FakeDoc(text)))


def test_candidates_are_exact_substrings_and_aliases_are_mapped(fake_pipeline):
    record = {"text": TEXT, "region_language": ["English"]}
    result = nlp.annotate_record(record, SCHEMA)
    assert result["status"] == "ok" and "plain" not in result["fields"]
    for candidates in result["fields"].values():
        for c in candidates:
            assert TEXT[c["start"]:c["end"]] == c["text"]
    assert [c["text"] for c in result["fields"]["position_holder"]] == ["Rousseau"]  # PER -> PERSON
    assert [c["text"] for c in result["fields"]["place"]] == ["Geneva"]  # GPE satisfies LOC
    assert [c["text"] for c in result["fields"]["terms"]] == ["Rousseau", "Geneva"]


def test_hints_go_stale_when_the_text_changes(fake_pipeline):
    record = {"text": TEXT, "region_language": ["English"]}
    nlp.annotate_record(record, SCHEMA)
    assert nlp.prompt_hints(record, ["position_holder"]) == {"position_holder": ["Rousseau"]}
    record["text"] = TEXT + " again"
    assert nlp.prompt_hints(record, ["position_holder"]) == {}


def test_record_terms_are_exact_spans_computed_without_tagged_fields(fake_pipeline):
    record = {"text": TEXT, "region_language": ["English"]}
    result = nlp.annotate_record(record, NS(fields=[]))
    assert result["status"] == "ok" and result["fields"] == {}
    # Entities win over the PROPN run covering the same characters.
    assert [(t["text"], t["source"], t["tag"]) for t in result["terms"]] == [
        ("Rousseau", "ner", "PERSON"),
        ("Geneva", "ner", "GPE"),
    ]
    assert nlp.current_terms(record) == result["terms"]
    record["text"] = TEXT + " again"
    assert nlp.current_terms(record) is None


def test_missing_model_is_reported_not_silently_empty(monkeypatch):
    monkeypatch.setattr(nlp, "load_pipeline", lambda language: None)
    record = {"text": TEXT, "region_language": ["fr"]}
    result = nlp.annotate_record(record, SCHEMA)
    assert result["status"] == "unavailable" and result["reason"] == "model_not_installed"
    assert nlp.prompt_hints(record, ["position_holder"]) == {}


def test_unsupported_language_and_untagged_schemas_are_skipped():
    assert nlp.annotate_record({"text": TEXT, "region_language": ["Klingon"]}, SCHEMA)["reason"] == "language_not_supported"
    assert nlp.annotate_record({"text": " "}, NS(fields=[NS(name="x", pos_tags=[], ner_tags=[])]))["status"] == "skipped"
    assert nlp.language_code("Français") == "fr" and nlp.language_code("en-US") == "en"


def test_real_spacy_pipeline_when_installed():
    spacy = pytest.importorskip("spacy")
    try:
        spacy.load(nlp.DEFAULT_MODELS["en"], exclude=["parser", "lemmatizer"])
    except Exception:
        pytest.skip("English model not installed")
    record = {"text": "Rousseau argues, against Hobbes, that Geneva is not Paris.", "region_language": ["English"]}
    result = nlp.annotate_record(record, SCHEMA)
    names = {c["text"] for c in result["fields"]["position_holder"]}
    assert {"Rousseau", "Hobbes"} <= names



def test_pos_candidates_drop_function_word_only_runs(monkeypatch):
    class StopDoc:
        ents = []

        def __iter__(self):
            return iter([
                Tok("the", "DET", 0, is_stop=True),
                Tok("argument", "NOUN", 4, is_stop=False),
            ])

    monkeypatch.setattr(nlp, "load_pipeline", lambda language: (lambda text: StopDoc()))
    schema = NS(fields=[NS(name="label", pos_tags=["DET", "NOUN"], ner_tags=[])])
    record = {"text": "the argument", "region_language": ["English"]}
    result = nlp.annotate_record(record, schema)
    assert [item["text"] for item in result["fields"]["label"]] == ["argument"]


def test_annotation_run_summary_names_spacy_model_and_language(fake_pipeline, monkeypatch):
    monkeypatch.setattr(nlp, "_engine_version", lambda: "3.8.7")
    records = [
        {"text": TEXT, "region_language": ["Français"]},
        {"text": TEXT, "region_language": ["Français"]},
    ]
    results = [nlp.annotate_record(record, SCHEMA) for record in records]
    summary = nlp.annotation_run_summary(results)
    assert summary["status"] == "ok"
    assert summary["engine"] == "spacy"
    assert summary["engine_version"] == "3.8.7"
    assert summary["languages"] == ["fr"]
    assert summary["records_annotated"] == 2

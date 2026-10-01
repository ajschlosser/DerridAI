# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic semantic identity: when two metadata values are the same value."""

from __future__ import annotations

import pytest
from app.metadata_schema import (
    MetadataSchema,
    SchemaField,
    default_schema,
    export_schema,
    import_schema,
)
from app.semantic_identity import (
    EquivalenceProfile,
    canonical_value_key,
    compare_values,
    set_default_lemmatizer,
)
from app.semantic_identity_registry import (
    SemanticIdentityRegistry,
    project_document_intelligence,
    project_reviewed_metadata,
    register_reviewed_alias,
    registry_for_record,
)

NAME = EquivalenceProfile(mode="entity_name", identity_kind="person")
PHRASE = EquivalenceProfile(mode="lexical_phrase", identity_kind="concept")
TEXT = EquivalenceProfile(mode="text")

# A tiny deterministic stand-in for spaCy: enough morphology for these phrases.
_LEMMAS = {"pushing": ("push", "VERB"), "push": ("push", "VERB"), "boundaries": ("boundary", "NOUN"),
           "boundary": ("boundary", "NOUN"), "supports": ("support", "VERB"), "support": ("support", "VERB"),
           "does": ("do", "AUX"), "not": ("not", "PART"), "n't": ("not", "PART"), "reject": ("reject", "VERB"),
           "critique": ("critique", "NOUN"), "deconstruction": ("deconstruction", "NOUN"),
           "metaphysics": ("metaphysics", "NOUN"), "against": ("against", "ADP"), "the": ("the", "DET"),
           "of": ("of", "ADP"), "better": ("well", "ADJ"), "good": ("good", "ADJ"), "reading": ("reading", "NOUN")}


def fake_lemmatizer(text: str, language: str):
    if language != "en":
        return None
    out = []
    for word in text.replace("n't", " n't").split():
        lemma, pos = _LEMMAS.get(word.casefold(), (word.casefold(), "X"))
        out.append((word, lemma, pos))
    return out


def phrase(left, right, **kw):
    return compare_values(left, right, profile=PHRASE, language="en", lemmatizer=fake_lemmatizer, **kw)


@pytest.mark.parametrize("left,right", [("J. P. Dingus", "J.P. Dingus"), ("J.P. Dingus", "JP Dingus"),
                                        ("J. P. Dingus", "JP Dingus"), ("Dingus, J. P.", "J. P. Dingus"),
                                        ("Jane  Author", "jane author")])
def test_entity_name_variants_are_equivalent(left, right):
    result = compare_values(left, right, profile=NAME)
    assert result.relation == "equivalent"
    assert result.left_key == result.right_key


@pytest.mark.parametrize("left,right", [("J. Dingus", "John Dingus"), ("Dingus", "J. P. Dingus"),
                                        ("Levinas", "Lévinas")])
def test_possible_but_unestablished_names_are_unknown(left, right):
    assert compare_values(left, right, profile=NAME).relation == "unknown"


def test_unrelated_names_are_different_and_suffixes_are_not_inversions():
    assert compare_values("Author", "Levinas", profile=NAME).relation == "different"
    assert compare_values("Dingus, Jr.", "Jr. Dingus", profile=NAME).relation != "equivalent"


def test_lexical_phrase_equivalence_keeps_negation_modifiers_and_prepositions():
    assert phrase("pushing the boundaries", "push the boundaries").relation == "equivalent"
    assert phrase("pushing against the boundaries", "push the boundaries").relation == "different"
    assert phrase("push the boundaries", "reject the boundaries").relation == "different"
    assert phrase("supports deconstruction", "does not support deconstruction").relation == "different"
    assert phrase("critique of metaphysics", "deconstruction of metaphysics").relation == "different"
    assert phrase("better reading", "good reading").relation == "different"
    assert phrase("does not support", "doesn't support").relation == "equivalent"


def test_missing_lemmatizer_is_unknown_never_a_guess():
    none = lambda text, language: None  # noqa: E731
    result = compare_values("pushing the boundaries", "push the boundaries", profile=PHRASE, language="en", lemmatizer=none)
    assert result.relation == "unknown"
    assert "lemmatizer_unavailable" in result.reason_codes
    # Surface normalization is still safe, and clearly unrelated phrases are still different.
    assert compare_values("Push the Boundaries", "push  the boundaries", profile=PHRASE, language="en", lemmatizer=none).relation == "equivalent"
    assert compare_values("critique of metaphysics", "deconstruction of metaphysics", profile=PHRASE, language="en", lemmatizer=none).relation == "different"
    # An unknown language never borrows English morphology.
    assert compare_values("pushing the boundaries", "push the boundaries", profile=PHRASE, language="", lemmatizer=fake_lemmatizer).relation == "unknown"


def test_default_lemmatizer_can_be_installed_for_the_process():
    set_default_lemmatizer(fake_lemmatizer)
    try:
        assert compare_values("pushing the boundaries", "push the boundaries", profile=PHRASE, language="en").relation == "equivalent"
    finally:
        set_default_lemmatizer(None)


def test_lists_need_one_to_one_equivalence_and_respect_ordering():
    assert compare_values(["J.P. Dingus", "Author"], ["Author", "JP Dingus"], profile=NAME).relation == "equivalent"
    assert compare_values(["Author", "Levinas"], ["Author"], profile=NAME).relation == "different"
    # Partial overlap is not equivalence.
    assert compare_values(["Author", "Levinas"], ["Author", "Husserl"], profile=NAME).relation == "different"
    # "J. Author" might be "Author", but nothing establishes it.
    assert compare_values(["Author", "Levinas"], ["Levinas", "J. Author"], profile=NAME).relation == "unknown"
    ordered = EquivalenceProfile(mode="text", collection_semantics="ordered")
    assert compare_values(["a", "b"], ["b", "a"], profile=ordered).relation == "different"
    assert compare_values(["a", "b"], ["b", "a"], profile=TEXT).relation == "equivalent"
    assert compare_values("Author", ["author"], profile=TEXT).relation == "equivalent"


def test_exact_and_controlled_profiles():
    exact = EquivalenceProfile(mode="exact")
    assert compare_values("Yes", "yes", profile=exact).relation == "different"
    assert compare_values(True, True, profile=exact).relation == "exact"
    assert compare_values(1, True, profile=exact).relation == "different"
    controlled = EquivalenceProfile(mode="controlled")
    assert compare_values("Endorses", "endorses", profile=controlled).relation == "equivalent"
    assert compare_values("endorses", "rejects", profile=controlled).relation == "different"
    assert compare_values(None, "", profile=TEXT).relation == "equivalent"
    assert compare_values(None, "x", profile=TEXT).relation == "different"


def test_reviewed_aliases_outrank_normalization_both_ways():
    registry = SemanticIdentityRegistry()
    register_reviewed_alias(registry, kind="person", canonical_label="Jane Author", aliases=["J. Author", "Author, Jane"], mode="entity_name")
    same = compare_values("J. Author", "Jane Author", profile=NAME, registry=registry)
    assert same.relation == "equivalent" and same.reason_codes == ["shared_semantic_identity"]
    # Two reviewed people whose names normalize alike are never merged by punctuation rules.
    registry = SemanticIdentityRegistry()
    a = register_reviewed_alias(registry, kind="person", canonical_label="J. P. Dingus", aliases=[], mode="entity_name")
    b = register_reviewed_alias(registry, kind="person", canonical_label="JP Dingus", aliases=[], mode="entity_name")
    distinct = compare_values("J. P. Dingus", "JP Dingus", profile=NAME, registry=registry)
    assert distinct.relation == "different"
    assert {distinct.left_identity_id, distinct.right_identity_id} == {a.identity_id, b.identity_id}
    assert compare_values("J.P. Dingus", "JP Dingus", profile=NAME, registry=registry).relation == "unknown"


def test_identities_are_scoped_by_kind():
    registry = SemanticIdentityRegistry()
    register_reviewed_alias(registry, kind="person", canonical_label="Jane Author", aliases=["Author"], mode="entity_name")
    concept = EquivalenceProfile(mode="text", identity_kind="concept")
    assert compare_values("Author", "Jane Author", profile=concept, registry=registry).relation == "different"


def test_document_intelligence_resolves_ambiguity_but_never_overrides_a_difference():
    registry = SemanticIdentityRegistry()
    project_document_intelligence(registry, {"provider": "booknlp", "model": "big", "entity_clusters": [
        {"cluster_id": "c1", "canonical": "Jane Author", "aliases": ["Author", "he", "Jane Author"], "entity_type": "PERSON"},
    ]})
    resolved = compare_values("Author", "Jane Author", profile=NAME, registry=registry)
    assert resolved.relation == "equivalent"
    assert "document_intelligence_alias" in resolved.reason_codes
    # A pronoun in a coreference cluster is still not the person's name.
    assert compare_values("he", "Jane Author", profile=NAME, registry=registry).relation == "different"
    ref = registry.resolve(value="Author", kind="person", mode="entity_name")
    assert ref is not None and ref.source_ids == ["booknlp:big:c1"]


def test_record_projection_bound_to_other_text_is_ignored():
    record = {"text": "Author wrote.", "document_intelligence": {
        "record_text_sha256": "stale", "provider": "spacy",
        "entities": [{"entity_id": "c1", "label": "Jane Author", "text": "Author", "entity_type": "PERSON"}]}}
    assert len(registry_for_record(record)) == 0
    record["document_intelligence"].pop("record_text_sha256")
    assert len(registry_for_record(record)) == 1


def test_reviewed_metadata_projects_only_human_values():
    schema = default_schema()
    reviewed = {"record_id": "r1", "text": "t", "persons": ["J.P. Dingus"],
                "metadata_field_status": {"persons": {"status": "human_confirmed", "method": "human"}}}
    unreviewed = {"record_id": "r2", "text": "t", "persons": ["Someone Else"],
                  "metadata_field_status": {"persons": {"status": "model_inferred", "method": "llm"}}}
    registry = SemanticIdentityRegistry()
    assert project_reviewed_metadata(registry, [reviewed, unreviewed], schema) == 1
    assert registry.resolve(value="JP Dingus", kind="person", mode="entity_name") is not None
    assert registry.resolve(value="Someone Else", kind="person", mode="entity_name") is None
    # Two observed reviewed values are not a claim that they name different people.
    other = {**reviewed, "record_id": "r3", "persons": ["Dingus"]}
    project_reviewed_metadata(registry, [other], schema)
    assert compare_values("Dingus", "J.P. Dingus", profile=NAME, registry=registry).relation == "unknown"


def test_canonical_value_key_prefers_identity_and_is_none_when_unsafe():
    assert canonical_value_key("J.P. Dingus", profile=NAME) == canonical_value_key("JP Dingus", profile=NAME)
    assert canonical_value_key(["b", "a"], profile=TEXT) == canonical_value_key(["A", "B"], profile=TEXT)
    none = lambda text, language: None  # noqa: E731
    assert canonical_value_key("pushing the boundaries", profile=PHRASE, language="en", lemmatizer=none) is None
    registry = SemanticIdentityRegistry()
    ref = register_reviewed_alias(registry, kind="person", canonical_label="Jane Author", aliases=["J. Author"], mode="entity_name")
    assert canonical_value_key("J. Author", profile=NAME, registry=registry) == ref.identity_id


def test_schema_resolves_policy_by_stable_semantics_and_round_trips():
    schema = default_schema()
    assert schema.equivalence_profile_for("persons").mode == "entity_name"
    assert schema.equivalence_profile_for("speaker").identity_kind == schema.equivalence_profile_for("persons").identity_kind == "person"
    assert schema.equivalence_profile_for("concepts").mode == "lexical_phrase"
    assert schema.equivalence_profile_for("quotation_chain").collection_semantics == "ordered"
    assert schema.equivalence_profile_for("is_direct_quote").mode == "exact"
    assert schema.equivalence_profile_for("region_type").mode == "controlled"
    with pytest.raises(KeyError):
        schema.equivalence_profile_for("no_such_field")
    # A renamed field keeps its policy; a custom field without one falls back to its type.
    body = schema.model_dump(mode="json")
    for field in body["fields"]:
        if field["name"] == "persons":
            field["name"] = "people_named"
    body["fields"].append({"name": "motif", "label": "Motif", "type": "list", "group": "indexing",
                           "equivalence_profile": {"mode": "lexical_phrase", "identity_kind": "motif"}})
    body["fields"].append({"name": "mood", "label": "Mood", "type": "choice", "group": "indexing", "strict": True,
                           "values": [{"value": "calm"}]})
    renamed = MetadataSchema.model_validate(body)
    assert renamed.equivalence_profile_for("people_named").mode == "entity_name"
    assert renamed.equivalence_profile_for("motif").identity_kind == "motif"
    assert renamed.equivalence_profile_for("mood").mode == "controlled"
    assert import_schema(export_schema(renamed)).equivalence_profile_for("motif").mode == "lexical_phrase"
    with pytest.raises(ValueError):
        SchemaField(name="bad", label="Bad", equivalence_profile={"mode": "fuzzy"})


def test_unset_policy_does_not_change_a_schema_hash():
    schema = default_schema()
    before = schema.content_hash()
    body = schema.model_dump(mode="json")
    for field in body["fields"]:
        field.pop("equivalence_profile")
    assert MetadataSchema.model_validate(body).content_hash() == before
    body["fields"][0]["equivalence_profile"] = {"mode": "exact"}
    assert MetadataSchema.model_validate(body).content_hash() != before


def test_builtin_profiles_declare_person_character_and_concept_policies():
    from app.metadata_schema_profiles.fiction import fiction_schema
    from app.metadata_schema_profiles.nonfiction import nonfiction_schema

    fiction, nonfiction = fiction_schema(), nonfiction_schema()
    assert fiction.equivalence_profile_for("dialogue_speakers").mode == "entity_name"
    # A fictional character never shares an identity with a real person of the same name.
    assert fiction.equivalence_profile_for("characters_present").identity_kind == "character"
    assert nonfiction.equivalence_profile_for("persons").identity_kind == "person"
    assert fiction.equivalence_profile_for("motifs").mode == "lexical_phrase"
    assert nonfiction.equivalence_profile_for("topics").mode == "lexical_phrase"


def test_lemma_tokens_reuse_the_annotation_pipeline_and_require_a_lemmatizer(monkeypatch):
    from types import SimpleNamespace

    from app import nlp_annotations

    class Pipeline:
        def __init__(self, names):
            self.pipe_names = names

        def __call__(self, text):
            return [SimpleNamespace(text=w, lemma_=w.rstrip("s"), pos_="NOUN") for w in text.split()]

    monkeypatch.setattr(nlp_annotations, "load_pipeline", lambda code: Pipeline(["tagger", "lemmatizer"]))
    assert nlp_annotations.lemma_tokens("boundaries", "English") == [("boundaries", "boundarie", "NOUN")]
    # The multilingual entity fallback has no lemmatizer: unavailable, not surface text.
    monkeypatch.setattr(nlp_annotations, "load_pipeline", lambda code: Pipeline(["ner"]))
    assert nlp_annotations.lemma_tokens("boundaries", "en") is None
    assert nlp_annotations.lemma_tokens("boundaries", "") is None

# Copyright 2026 Aaron John Schlosser, PhD.
"""Reviewed aliases and the derived projections that consume semantic identity.

Why: the Semantic Content Graph and Record semantic maps must collapse values that are
the same identity while keeping every surface form, and must never merge identities a
reviewer established as distinct. Reviewed aliases are canonical reviewer state; the
graph only projects them.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.enrichment_ledger import ACCEPTED, UNRESOLVED
from app.metadata_schema import default_schema
from app.nlp_annotations import record_terms, text_digest
from app.record_semantic_map import record_semantic_map, semantic_node_neighborhood
from app.semantic_content_graph import build_semantic_content_graph
from app.semantic_identity import SEMANTIC_IDENTITY_VERSION, set_default_lemmatizer
from app.semantic_identity_registry import (
    SemanticIdentityRegistry,
    register_reviewed_alias,
)
from app.semantic_identity_store import (
    AliasConflict,
    build_registry,
    create_alias_set,
    list_alias_sets,
    retire_alias_set,
)
from test_review_value_equivalence import install, review_rows


def lemmas(text, language):
    table = {"pushing": ("push", "VERB"), "push": ("push", "VERB"), "boundaries": ("boundary", "NOUN")}
    return [(w, *table.get(w.casefold(), (w.casefold(), "X"))) for w in text.split()]


@pytest.fixture
def lemmatizer():
    set_default_lemmatizer(lemmas)
    yield
    set_default_lemmatizer(None)


def reviewed(record_id, **fields):
    status = {name: {"status": "human_confirmed", "method": "human"} for name in fields}
    return {"record_id": record_id, "record_revision": 1, "text": "t", "language": "en", "metadata_field_status": status, **fields}


def unreviewed(record_id, **fields):
    status = {name: {"status": "model_inferred", "method": "llm"} for name in fields}
    return {"record_id": record_id, "record_revision": 1, "text": "t", "language": "en", "metadata_field_status": status, **fields}


def nodes_by_type(graph, kind):
    return [node for node in graph["nodes"] if node["type"] == kind]


# --- reviewed alias sets ---------------------------------------------------------------------

def test_alias_sets_are_audited_and_never_share_a_surface(tmp_path):
    repo, build, _ = install(tmp_path, "speaker", "J. Derrida")
    bid = build["build_id"]
    first = create_alias_set(repo, bid, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida", " j.  derrida ", ""], reviewer="rev-1")
    assert first["aliases"] == ["J. Derrida"] and first["reviewer"] == "rev-1"
    with pytest.raises(AliasConflict):
        create_alias_set(repo, bid, kind="person", canonical_label="J. Derrida", aliases=[])
    # Similar-looking names may belong to different people; that is a reviewer's call.
    create_alias_set(repo, bid, kind="person", canonical_label="J. P. Dingus", aliases=[])
    create_alias_set(repo, bid, kind="person", canonical_label="JP Dingus", aliases=[])
    # The same surface in another kind is another identity.
    create_alias_set(repo, bid, kind="concept", canonical_label="Derrida", aliases=[])
    replaced = create_alias_set(repo, bid, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida", "Derrida, Jacques"], replaces=first["alias_set_id"])
    old = next(item for item in list_alias_sets(repo, bid, include_retired=True) if item["alias_set_id"] == first["alias_set_id"])
    assert old["retired_at"] and old["replaced_by"] == replaced["alias_set_id"]
    assert len(list_alias_sets(repo, bid)) == 4
    retire_alias_set(repo, bid, replaced["alias_set_id"])
    assert len(list_alias_sets(repo, bid)) == 3
    with pytest.raises(KeyError):
        retire_alias_set(repo, bid, replaced["alias_set_id"])
    with pytest.raises(ValueError):
        create_alias_set(repo, bid, kind="Not A Kind", canonical_label="x", aliases=[])


def test_reviewed_alias_turns_an_unresolved_review_into_an_acceptance(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J. Derrida")
    bid = build["build_id"]
    listed = manager.semantic_aliases(bid)
    assert any(item["kind"] == "person" and "speaker" in item["fields"] for item in listed["kinds"])
    manager.save_semantic_alias(bid, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida"])
    manager.patch_metadata(bid, "r1", {"speaker": "Jacques Derrida"}, expected_revision=1)
    rows = review_rows(manager)
    assert [row["kind"] for row in rows] == [ACCEPTED]
    assert rows[0]["equivalence_reasons"] == ["shared_semantic_identity"] and rows[0]["semantic_identity_id"]
    assert not repo.load_records(bid)[0].get("llm_rejections")


def test_without_the_alias_the_same_edit_is_neutral(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J. Derrida")
    manager.patch_metadata(build["build_id"], "r1", {"speaker": "Jacques Derrida"}, expected_revision=1)
    assert [row["kind"] for row in review_rows(manager)] == [UNRESOLVED]


# --- Semantic Content Graph ------------------------------------------------------------------

def test_graph_collapses_equivalent_values_and_keeps_every_surface():
    records = [reviewed("r1", persons=["J.P. Dingus"]), unreviewed("r2", persons=["JP Dingus"]),
               unreviewed("r3", persons=["JP Dingus"]), unreviewed("r4", persons=["Levinas"])]
    graph = build_semantic_content_graph(records, schema=default_schema())
    people = nodes_by_type(graph, "person")
    assert len(people) == 2
    dingus = next(node for node in people if "JP Dingus" in node["surface_forms"])
    # A reviewed value outranks a more frequent unreviewed one for the display label.
    assert dingus["label"] == "J.P. Dingus" and dingus["surface_forms"] == ["J.P. Dingus", "JP Dingus"]
    assert sorted(dingus["record_ids"]) == ["r1", "r2", "r3"]
    assert dingus["canonical_value_key"] == "person:entity_name:j p dingus"
    assert dingus["identity_version"] == SEMANTIC_IDENTITY_VERSION == graph["identity_version"]
    # Metadata is never rewritten by the projection.
    assert records[1]["persons"] == ["JP Dingus"]


def test_graph_never_merges_distinct_reviewed_identities(tmp_path):
    repo, build, _ = install(tmp_path, "speaker", "x")
    bid = build["build_id"]
    create_alias_set(repo, bid, kind="person", canonical_label="J. P. Dingus", aliases=[])
    create_alias_set(repo, bid, kind="person", canonical_label="JP Dingus", aliases=["Jean-Paul Dingus"])
    schema = default_schema()
    records = [unreviewed("r1", persons=["J. P. Dingus"]), unreviewed("r2", persons=["JP Dingus"]), unreviewed("r3", persons=["Jean-Paul Dingus"])]
    graph = build_semantic_content_graph(records, schema=schema, registry=build_registry(repo, bid, schema=schema))
    people = nodes_by_type(graph, "person")
    assert len(people) == 2
    jean_paul = next(node for node in people if "Jean-Paul Dingus" in node["surface_forms"])
    # The reviewed alias's canonical label names the node, and the alias joins it.
    assert jean_paul["label"] == "JP Dingus" and sorted(jean_paul["record_ids"]) == ["r2", "r3"]
    assert jean_paul["identity_id"]


def test_graph_lexical_identity_uses_lemmas_when_available(lemmatizer):
    records = [unreviewed("r1", concepts=["pushing the boundaries"]), unreviewed("r2", concepts=["push the boundaries"]),
               unreviewed("r3", concepts=["critique of metaphysics"]), unreviewed("r4", concepts=["deconstruction of metaphysics"])]
    graph = build_semantic_content_graph(records, schema=default_schema())
    concepts = nodes_by_type(graph, "concept")
    assert len(concepts) == 3
    assert any(set(node["surface_forms"]) == {"pushing the boundaries", "push the boundaries"} for node in concepts)


def test_graph_without_a_lemmatizer_keeps_inflected_phrases_apart():
    records = [unreviewed("r1", concepts=["pushing the boundaries"]), unreviewed("r2", concepts=["push the boundaries"])]
    set_default_lemmatizer(lambda text, language: None)
    try:
        graph = build_semantic_content_graph(records, schema=default_schema())
    finally:
        set_default_lemmatizer(None)
    assert len(nodes_by_type(graph, "concept")) == 2


def analysis(provider, clusters):
    return {"status": "ok", "provider": provider, "model": "m", "entity_clusters": clusters, "entities": [], "record_spans": []}


def test_surface_clusters_merge_but_booknlp_characters_with_one_name_do_not():
    spacy = analysis("spacy", [
        {"cluster_id": "spacy-1", "canonical": "J.P. Dingus", "aliases": ["J.P. Dingus"], "entity_type": "PERSON"},
        {"cluster_id": "spacy-2", "canonical": "JP Dingus", "aliases": ["JP Dingus"], "entity_type": "PERSON"},
    ])
    graph = build_semantic_content_graph([], spacy, schema=default_schema())
    [person] = nodes_by_type(graph, "person")
    assert person["cluster_ids"] == ["spacy-1", "spacy-2"]
    merged_id = next(old for old, new in graph["node_aliases"].items() if new == person["id"])
    assert semantic_node_neighborhood(graph, [], merged_id)["node"]["id"] == person["id"]

    booknlp = analysis("booknlp", [
        {"cluster_id": "1", "canonical": "John", "aliases": ["John"], "entity_type": "PERSON"},
        {"cluster_id": "2", "canonical": "John", "aliases": ["John"], "entity_type": "PERSON"},
    ])
    graph = build_semantic_content_graph([], booknlp, schema=default_schema())
    assert len(nodes_by_type(graph, "person")) == 2


def test_person_metadata_attaches_to_the_document_entity_by_identity():
    doc = analysis("booknlp", [{"cluster_id": "7", "canonical": "Jacques Derrida", "aliases": ["J. Derrida", "Derrida"], "entity_type": "PERSON"}])
    graph = build_semantic_content_graph([reviewed("r1", persons=["J Derrida"])], doc, schema=default_schema())
    [person] = nodes_by_type(graph, "person")
    assert person["cluster_ids"] == ["7"] and "J Derrida" in person["surface_forms"]
    assert person["label"] == "J Derrida"  # the reviewed value outranks the provider's label


def test_identities_are_scoped_by_kind_in_the_graph():
    registry = SemanticIdentityRegistry()
    register_reviewed_alias(registry, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida"], mode="entity_name")
    graph = build_semantic_content_graph([unreviewed("r1", concepts=["J. Derrida"]), unreviewed("r2", persons=["J. Derrida"])],
                                         schema=default_schema(), registry=registry)
    assert len(nodes_by_type(graph, "concept")) == 1 and len(nodes_by_type(graph, "person")) == 1


# --- Record semantic map and term identity ---------------------------------------------------

def term(text, surface, identity, source, tag):
    start = text.index(surface)
    row = {"start": start, "end": start + len(surface), "text": surface, "source": source, "tag": tag}
    if identity:
        row["identity_text"] = identity
    return row


def test_terms_join_nodes_by_identity_and_keep_exact_spans(lemmatizer):
    text = "He spoke of pushing boundaries and of J.P. Dingus."
    terms = [term(text, "pushing boundaries", "push boundary", "pos", "VERB+NOUN"), term(text, "J.P. Dingus", "j p dingus", "ner", "PERSON")]
    record = {**unreviewed("r1", concepts=["push boundaries"], persons=["JP Dingus"]), "text": text,
              "nlp_candidates": {"status": "ok", "terms": terms, "text_sha256": text_digest(text)}}
    graph = build_semantic_content_graph([record], schema=default_schema())
    view = record_semantic_map(graph, [record], "r1")
    by_text = {m["text"]: m for m in view["mentions"]}
    concept = next(node for node in graph["nodes"] if node["type"] == "concept")
    person = next(node for node in graph["nodes"] if node["type"] == "person")
    assert by_text["pushing boundaries"]["node_id"] == concept["id"]
    assert by_text["J.P. Dingus"]["node_id"] == person["id"]
    for mention in view["mentions"]:
        assert text[mention["start"]:mention["end"]] == mention["text"]


def test_unmatched_equivalent_terms_share_one_term_node_and_unknown_ones_do_not():
    text = "boundaries; boundary; limits"
    terms = [term(text, "boundaries", "boundary", "pos", "NOUN"), term(text, "boundary;", "", "pos", "NOUN"), term(text, "limits", "", "pos", "NOUN")]
    terms[1] = {**term(text, "boundary;", "boundary", "pos", "NOUN")}
    terms[1]["end"] -= 1
    terms[1]["text"] = "boundary"
    record = {**unreviewed("r1"), "text": text, "nlp_candidates": {"status": "ok", "terms": terms, "text_sha256": text_digest(text)}}
    view = record_semantic_map(build_semantic_content_graph([record]), [record], "r1")
    ids = [m["node_id"] for m in view["mentions"]]
    assert ids[0] == ids[1] != ids[2]


def test_record_terms_carry_identity_only_when_lemmas_exist():
    def token(text, idx, lemma, pos):
        return SimpleNamespace(text=text, idx=idx, lemma_=lemma, pos_=pos)

    class Doc(list):
        ents: list = []

        def char_span(self, start, end):
            return [t for t in self if t.idx >= start and t.idx + len(t.text) <= end]

    text = "boundaries matter"
    with_lemmas = Doc([token("boundaries", 0, "boundary", "NOUN"), token("matter", 11, "matter", "VERB")])
    [found] = record_terms(with_lemmas, text)
    assert found["text"] == "boundaries" == text[found["start"]:found["end"]]
    assert found["identity_text"] == "boundary" and found["identity_version"] == SEMANTIC_IDENTITY_VERSION
    without = Doc([token("boundaries", 0, "", "NOUN"), token("matter", 11, "", "VERB")])
    assert "identity_text" not in record_terms(without, text)[0]


# --- precedent retrieval ---------------------------------------------------------------------

def test_match_conditions_compare_reviewed_values_by_identity(tmp_path):
    from app.metadata_exemplar_retrieval import match_tier
    from app.semantic_identity_store import reviewed_value_relation

    repo, build, _ = install(tmp_path, "speaker", "x")
    relation = reviewed_value_relation(repo, build["build_id"], default_schema())
    precedent = {"reviewed_values": {"speaker": '"J.P. Dingus"'}}
    # A restated reviewed value agrees instead of contradicting.
    assert match_tier(precedent, {"speaker": '"JP Dingus"'}, ["speaker"], relation) == ("matched", ["speaker"])
    assert match_tier(precedent, {"speaker": '"JP Dingus"'}, ["speaker"]) == ("differs", ["speaker"])
    assert match_tier(precedent, {"speaker": '"Levinas"'}, ["speaker"], relation) == ("differs", ["speaker"])
    # Unknown is skipped, not guessed either way.
    assert match_tier(precedent, {"speaker": '"J. Dingus"'}, ["speaker"], relation) == ("not_compared", [])


def test_selection_prefers_distinct_identities_but_keeps_every_precedent():
    from app.metadata_exemplar_retrieval import _identity_first

    canonical = {
        "a": {"canonical_value_key": "person:entity_name:j p dingus"},
        "b": {"canonical_value_key": "person:entity_name:j p dingus"},
        "c": {"canonical_value_key": "person:entity_name:levinas"},
        "d": {"canonical_value_key": None},
        "e": {"canonical_value_key": None},
    }
    rows = [{"id": key} for key in "abcde"]
    first, rest = _identity_first(rows, canonical)
    assert [row["id"] for row in first] == ["a", "c", "d", "e"] and [row["id"] for row in rest] == ["b"]


def test_projection_metadata_carries_identity_beside_exact_values():
    from app.metadata_exemplar_retrieval import _projection

    row = _projection({"metadata_exemplar_id": "mex-1", "field_value": "J.P. Dingus", "canonical_value_key": "person:entity_name:j p dingus",
                       "semantic_identity_id": None, "equivalence_profile": "entity_name", "equivalence_version": 1}, "b")
    assert row["field_value_json"] == '"J.P. Dingus"'
    assert row["canonical_value_key"] == "person:entity_name:j p dingus" and row["semantic_identity_id"] == ""
    assert row["equivalence_version"] == 1
    identity_keys = ["canonical_value_key", "semantic_identity_id", "rejected_canonical_value_key",
                     "rejected_semantic_identity_id", "equivalence_profile", "equivalence_version"]
    assert all(row[key] is not None for key in identity_keys)  # Chroma metadata cannot hold None


# --- importing another corpus's reviewed identities ------------------------------------------

def second_build(repo, build):
    payload = {key: build[key] for key in ("asset_id", "source_sha256", "source_filename", "source_page_count", "source_block_count",
                                           "schema_version", "profile_id", "profile_version", "app_version", "provider", "model", "request")}
    other = repo.create_build({**payload, "manifest": {"title": "Of Grammatology"}})
    other["status"] = "review"; other["stage"] = "review"; repo.save_build(other)
    return other["build_id"]


def test_import_copies_identities_with_provenance_and_reports_clashes(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "J. Derrida")
    here, source = build["build_id"], second_build(repo, build)
    derrida = create_alias_set(repo, source, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida"], reviewer="rev-a")
    levinas = create_alias_set(repo, source, kind="person", canonical_label="Emmanuel Levinas", aliases=["E. Levinas"])
    create_alias_set(repo, here, kind="person", canonical_label="E. Levinas", aliases=[])  # already an identity here

    [listed] = manager.semantic_alias_sources(here)
    assert listed == {"build_id": source, "title": "Of Grammatology", "created_at": listed["created_at"], "alias_sets": 2, "kinds": ["person"]}

    result = manager.import_semantic_aliases(here, source)
    [copied] = result["imported"]
    assert copied["canonical_label"] == "Jacques Derrida" and copied["alias_set_id"] != derrida["alias_set_id"]
    assert copied["imported_from"]["build_id"] == source and copied["imported_from"]["alias_set_id"] == derrida["alias_set_id"]
    assert copied["imported_from"]["reviewer"] == "rev-a"
    [clash] = result["skipped"]
    assert clash["alias_set_id"] == levinas["alias_set_id"] and clash["reason"] == "conflict" and "E. Levinas" in clash["detail"]

    # A copy, not a link: the source can change without changing this corpus.
    retire_alias_set(repo, source, derrida["alias_set_id"])
    assert any(item["canonical_label"] == "Jacques Derrida" for item in list_alias_sets(repo, here))
    # The imported identity is used by this build's review.
    manager.patch_metadata(here, "r1", {"speaker": "Jacques Derrida"}, expected_revision=1)
    assert [row["kind"] for row in review_rows(manager)] == [ACCEPTED]


def test_import_is_selective_and_never_duplicates_an_import(tmp_path):
    repo, build, manager = install(tmp_path, "speaker", "x")
    here, source = build["build_id"], second_build(repo, build)
    derrida = create_alias_set(repo, source, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida"])
    create_alias_set(repo, source, kind="concept", canonical_label="différance", aliases=["differance"])
    first = manager.import_semantic_aliases(here, source, [derrida["alias_set_id"]])
    assert [item["canonical_label"] for item in first["imported"]] == ["Jacques Derrida"]
    # Editing the import keeps its provenance, so importing again skips it.
    edited = create_alias_set(repo, here, kind="person", canonical_label="Jacques Derrida", aliases=["J. Derrida", "Derrida"],
                              replaces=first["imported"][0]["alias_set_id"])
    assert edited["imported_from"]["alias_set_id"] == derrida["alias_set_id"]
    again = manager.import_semantic_aliases(here, source)
    assert [item["canonical_label"] for item in again["imported"]] == ["différance"]
    assert [(item["canonical_label"], item["reason"]) for item in again["skipped"]] == [("Jacques Derrida", "already_imported")]
    with pytest.raises(KeyError):
        manager.import_semantic_aliases(here, source, ["alias-missing"])
    with pytest.raises(ValueError):
        manager.import_semantic_aliases(here, here)

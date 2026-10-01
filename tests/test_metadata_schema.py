"""Metadata schemas: the built-in one reproduces today's prompts, and custom ones are validated and portable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from app import metadata_schema as ms
from app.corpus_metadata import (
    ATTRIBUTION_EVIDENCE_FIELDS,
    METADATA_FAMILY_FIELDS,
    REVIEW_METADATA_FIELDS,
)
from app.metadata_schema import MetadataSchema, SchemaField, SchemaGroup
from app.metadata_schema_profiles import (
    BUILTIN_SCHEMA_IDS,
    FICTION_SCHEMA_ID,
    NONFICTION_SCHEMA_ID,
    fiction_schema,
    nonfiction_schema,
)

LEGACY = json.loads((Path(__file__).parent / "fixtures" / "legacy_prompts.json").read_text(encoding="utf-8"))
CONTEXT = "<<CONTEXT>>\n"


def prompt(schema, group):
    return ms.build_group_prompt(schema, group, base_context=CONTEXT)


def test_the_built_in_schema_prompts_require_complete_assessments():
    schema = ms.default_schema()
    discourse = prompt(schema, "discourse")
    quotation = prompt(schema, "quotation")
    indexing = prompt(schema, "indexing")
    for text in (discourse, quotation, indexing):
        assert "field_assessments" in text
        assert "no_supported_value" in text
        assert "uncertain" in text
    assert "even when its metadata value is null or empty" in discourse
    assert "every one of is_direct_quote" in quotation
    assert "even when the corresponding metadata list is empty" in indexing


def test_group_prompt_and_response_contract_can_be_scoped_to_unresolved_fields():
    schema = ms.default_schema()
    scoped_prompt = ms.build_group_prompt(
        schema,
        "indexing",
        base_context=CONTEXT,
        field_names={"topics", "concepts"},
    )
    assert "- topics " in scoped_prompt
    assert "- concepts " in scoped_prompt
    assert "- persons " not in scoped_prompt
    assert "- works_referenced " not in scoped_prompt
    assert "topics and concepts" in scoped_prompt

    model = ms.response_model_for(
        schema,
        "indexing",
        field_names={"topics", "concepts"},
    )
    parsed = model.model_validate({
        "metadata": {"topics": ["hospitality"], "concepts": ["sovereignty"]},
        "field_assessments": {
            "topics": {
                "confidence": 0.9,
                "needs_review": False,
                "reason": "Explicit subject matter.",
                "outcome": "supported_value",
            },
            "concepts": {
                "confidence": 0.85,
                "needs_review": False,
                "reason": "Explicit conceptual vocabulary.",
                "outcome": "supported_value",
            },
        },
        "review_reason": "",
    })
    assert parsed.metadata.model_dump() == {
        "topics": ["hospitality"],
        "concepts": ["sovereignty"],
    }
    with pytest.raises(ValidationError):
        model.model_validate({
            "metadata": {
                "topics": ["hospitality"],
                "concepts": ["sovereignty"],
                "persons": ["Derrida"],
            },
            "field_assessments": {
                "topics": {
                    "confidence": 0.9,
                    "needs_review": False,
                    "reason": "Explicit.",
                    "outcome": "supported_value",
                },
                "concepts": {
                    "confidence": 0.85,
                    "needs_review": False,
                    "reason": "Explicit.",
                    "outcome": "supported_value",
                },
            },
            "review_reason": "",
        })


def test_response_consistency_degrades_assessment_value_contradictions_to_review():
    schema = ms.default_schema()
    model = ms.response_model_for(schema, "discourse")
    fields = {
        "region_type": "main_text",
        "primary_text": True,
        "discourse_role": "analysis",
        **{field.name: ([] if field.type == "list" else None) for field in schema.fields_in("discourse")},
    }
    assessed = ["region_type", "primary_text", "discourse_role", *[f.name for f in schema.fields_in("discourse") if f.assess]]
    assessments = {
        name: {"confidence": 0.95, "needs_review": False, "reason": "clear", "outcome": "no_supported_value"}
        for name in assessed
    }
    for name in ("region_type", "primary_text", "discourse_role"):
        assessments[name] = {"confidence": 0.95, "needs_review": False, "reason": "clear", "outcome": "supported_value"}
    evidence = {
        name: {"block_ids": ["b1"], "confidence": 0.95, "reason": "clear"}
        for name in ("region_type", "primary_text", "discourse_role")
    }
    model.model_validate({"metadata": fields, "field_assessments": assessments, "field_evidence": evidence})

    missing_value = json.loads(json.dumps({"metadata": fields, "field_assessments": assessments, "field_evidence": evidence}))
    missing_value["field_assessments"]["speaker"] = {
        "confidence": 0.95,
        "needs_review": False,
        "reason": "The speaker is clearly Derrida.",
        "outcome": "supported_value",
    }
    accepted = model.model_validate(missing_value)
    assert accepted.field_assessments.speaker.outcome == "uncertain"
    assert accepted.field_assessments.speaker.needs_review is True
    assert "contradiction" in accepted.field_assessments.speaker.reason.lower()

    contradictory_value = json.loads(json.dumps({"metadata": fields, "field_assessments": assessments, "field_evidence": evidence}))
    contradictory_value["metadata"]["speaker"] = "Jacques Derrida"
    contradictory_value["field_assessments"]["speaker"] = {
        "confidence": 0.95,
        "needs_review": False,
        "reason": "No speaker applies.",
        "outcome": "no_supported_value",
    }
    accepted = model.model_validate(contradictory_value)
    assert accepted.metadata.speaker == "Jacques Derrida"
    assert accepted.field_assessments.speaker.outcome == "uncertain"
    assert accepted.field_assessments.speaker.needs_review is True
    assert "no_supported_value" in accepted.field_assessments.speaker.reason

    uncertain = json.loads(json.dumps({"metadata": fields, "field_assessments": assessments, "field_evidence": evidence}))
    uncertain["field_assessments"]["speaker"] = {
        "confidence": 0.5,
        "needs_review": False,
        "reason": "uncertain",
        "outcome": "uncertain",
    }
    accepted = model.model_validate(uncertain)
    assert accepted.field_assessments.speaker.outcome == "uncertain"
    assert accepted.field_assessments.speaker.needs_review is True

    missing_evidence = json.loads(json.dumps({"metadata": fields, "field_assessments": assessments, "field_evidence": evidence}))
    missing_evidence["metadata"]["speaker"] = "Jacques Derrida"
    missing_evidence["field_assessments"]["speaker"] = {
        "confidence": 0.95,
        "needs_review": False,
        "reason": "clear",
        "outcome": "supported_value",
    }
    # Structured-output validation preserves the usable family response. Evidence
    # sufficiency is reconciled against current-record block IDs afterward, where
    # this field becomes evidence_failed/reviewable instead of failing the whole call.
    accepted = model.model_validate(missing_evidence)
    assert accepted.metadata.speaker == "Jacques Derrida"


def test_the_built_in_schema_describes_the_same_fields_as_the_code_does_today():
    schema = ms.default_schema()
    assert schema.family_fields() == {k: v - {"attribution_confidence", "semantic_classification_confidence"} for k, v in METADATA_FAMILY_FIELDS.items()}
    assert schema.attribution_fields() == set(ATTRIBUTION_EVIDENCE_FIELDS)
    assert set(schema.review_fields()) == set(REVIEW_METADATA_FIELDS)
    assert schema.review_fields()[:3] == list(ms.CORE_FIELDS)


def test_default_schema_cardinality_is_explicit_and_semantic():
    schema = ms.default_schema()
    by_name = schema.by_name()
    for name in (
        "quoted_speaker",
        "quoted_author",
        "quoted_work",
        "quoted_position_holder",
        "quoted_addressee",
        "quoted_referent",
    ):
        assert by_name[name].type == "text", name
    for name in ("semantic_function", "quotation_chain", "topics", "concepts", "persons", "works_referenced"):
        assert by_name[name].type == "list", name


def test_legacy_cardinality_normalization_is_lossless_or_explicitly_ambiguous():
    schema = ms.default_schema()
    quoted_speaker = schema.by_name()["quoted_speaker"]
    topics = schema.by_name()["topics"]

    assert ms.normalize_legacy_cardinality(quoted_speaker, ["Levinas"]) == ("Levinas", False)
    assert ms.normalize_legacy_cardinality(quoted_speaker, []) == (None, False)
    assert ms.normalize_legacy_cardinality(
        quoted_speaker, ["Levinas", "Heidegger"]
    ) == (["Levinas", "Heidegger"], True)
    assert ms.normalize_legacy_cardinality(topics, "hospitality") == (["hospitality"], False)
    assert ms.normalize_legacy_cardinality(topics, ["hospitality"]) == (["hospitality"], False)


@pytest.mark.parametrize(
    ("factory", "schema_id", "field_namespace", "required_fields", "corpus_fields"),
    [
        (
            fiction_schema,
            FICTION_SCHEMA_ID,
            "fiction",
            {
                "narrator",
                "point_of_view",
                "focalizers",
                "characters_present",
                "character_relationships",
                "locations",
                "setting_time",
                "events",
                "dialogue_speakers",
                "themes",
                "motifs",
                "symbols",
                "tone",
                "literary_devices",
            },
            {"fiction_form", "fiction_genres"},
        ),
        (
            nonfiction_schema,
            NONFICTION_SCHEMA_ID,
            "nonfiction",
            {
                "claim",
                "claim_type",
                "position_holder",
                "is_direct_quote",
                "quoted_speaker",
                "quoted_work",
                "quotation_chain",
                "evidence_items",
                "findings",
                "sources_cited",
                "statistics",
                "methods_or_procedures",
                "persons",
                "organizations",
                "places",
                "dates",
                "works_referenced",
                "laws_or_policies",
                "section_function",
                "recommendations",
                "conclusions",
                "limitations",
            },
            {"nonfiction_genre", "subject_domains", "intended_audience"},
        ),
    ],
)
def test_domain_builtin_profiles_are_traceable_guided_and_schema_driven(
    factory, schema_id, field_namespace, required_fields, corpus_fields
):
    schema = factory()
    by_name = schema.by_name()

    assert schema.id == schema_id
    assert schema.group("discourse")
    assert required_fields <= set(by_name)
    assert corpus_fields <= set(by_name)
    assert all(by_name[name].scope == "corpus" for name in corpus_fields)

    for field in schema.fields:
        assert field.instruction.strip(), field.name
        assert field.evidence is True, field.name
        assert field.assess is True, field.name
        assert field.field_id.startswith(f"derridai.profile.{field_namespace}."), field.name

    prompts = {
        group.key: ms.build_group_prompt(schema, group.key, base_context=CONTEXT)
        for group in schema.groups
    }
    for field in schema.fields:
        assert field.name in prompts[field.group]


def test_nonfiction_evidence_prompt_separates_attention_cues_from_metadata_values():
    schema = nonfiction_schema()
    by_name = schema.by_name()

    assert schema.schema_version == "1.0.1"
    for name in ("evidence_types", "evidence_items"):
        assert by_name[name].pos_tags == []
        assert by_name[name].ner_tags == []

    evidence_prompt = prompt(schema, "evidence")
    assert "supported_value requires a non-empty metadata value" in evidence_prompt
    assert "no_supported_value requires null or []" in evidence_prompt
    assert "never copy a candidate list into metadata" in evidence_prompt


def test_default_schema_assigns_curated_pos_and_ner_hints_to_every_configurable_field():
    schema = ms.default_schema()
    expected = {
        "region_author": (["PROPN"], ["PERSON", "ORG"]),
        "speaker": (["PRON", "PROPN", "NOUN"], ["PERSON", "ORG", "NORP"]),
        "position_holder": (["PRON", "PROPN", "NOUN"], ["PERSON", "ORG", "NORP"]),
        "target": (
            ["PROPN", "NOUN"],
            ["PERSON", "ORG", "NORP", "GPE", "LOC", "EVENT", "LAW", "LANGUAGE", "WORK_OF_ART"],
        ),
        "stance": ([], []),
        "proposition_status": ([], []),
        "claim_scope": (["ADJ", "NOUN", "PROPN"], []),
        "semantic_function": ([], []),
        "is_direct_quote": ([], []),
        "quoted_speaker": (["PRON", "PROPN", "NOUN"], ["PERSON", "ORG", "NORP"]),
        "quoted_author": (["PROPN"], ["PERSON", "ORG"]),
        "quoted_work": (["PROPN", "NOUN"], ["WORK_OF_ART", "LAW"]),
        "quoted_position_holder": (["PRON", "PROPN", "NOUN"], ["PERSON", "ORG", "NORP"]),
        "quoted_addressee": (["PRON", "PROPN", "NOUN"], ["PERSON", "ORG", "NORP"]),
        "quoted_referent": (
            ["PRON", "PROPN", "NOUN"],
            ["PERSON", "ORG", "NORP", "GPE", "LOC", "EVENT", "LAW", "LANGUAGE", "WORK_OF_ART"],
        ),
        "quotation_chain": (["PROPN"], ["PERSON", "ORG", "WORK_OF_ART"]),
        "topics": (
            ["ADJ", "NOUN", "PROPN"],
            ["EVENT", "GPE", "LOC", "NORP", "ORG", "LANGUAGE", "LAW"],
        ),
        "concepts": (["ADJ", "NOUN", "PROPN"], []),
        "persons": (["PROPN"], ["PERSON"]),
        "works_referenced": (["PROPN", "NOUN"], ["WORK_OF_ART", "LAW"]),
    }

    assert schema.schema_version == "2.0.0"
    assert set(schema.by_name()) == set(expected)
    for name, (pos_tags, ner_tags) in expected.items():
        field = schema.by_name()[name]
        assert field.pos_tags == pos_tags, name
        assert field.ner_tags == ner_tags, name


def test_the_output_shape_is_generated_and_matches_the_hand_written_models():
    from app import corpus_builder as cb

    schema = ms.default_schema()
    for group, legacy in (("discourse", cb.DiscourseMetadataResponseModel), ("quotation", cb.QuotationMetadataResponseModel), ("indexing", cb.IndexMetadataResponseModel)):
        model = ms.response_model_for(schema, group)
        got = set(model.model_json_schema()["$defs"][f"{group.title()}Metadata"]["properties"])
        want = set(legacy.model_json_schema()["$defs"][legacy.model_fields["metadata"].annotation.__name__]["properties"])
        want -= {"language"}  # the document language is inherited, not asked of the model
        assert got == want, group
    quotation_fields = ("is_direct_quote", "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder", "quoted_addressee", "quoted_referent", "quotation_chain")
    scalar_quotation_fields = quotation_fields[1:-1]
    answer = ms.response_model_for(schema, "quotation").model_validate({
        "metadata": {
            "is_direct_quote": None,
            **{name: None for name in scalar_quotation_fields},
            "quotation_chain": [],
        },
        "field_assessments": {name: {"confidence": 0.9, "needs_review": False, "reason": "clear", "outcome": "no_supported_value"} for name in quotation_fields},
    })
    assert answer.metadata.is_direct_quote is None
    assert answer.metadata.quoted_speaker is None
    assert answer.metadata.quotation_chain == []

    populated = ms.response_model_for(schema, "quotation").model_validate({
        "metadata": {
            "is_direct_quote": True,
            "quoted_speaker": "Emmanuel Levinas",
            **{name: None for name in scalar_quotation_fields if name != "quoted_speaker"},
            "quotation_chain": ["Derrida", "Levinas"],
        },
        "field_assessments": {name: {"confidence": 0.9, "needs_review": False, "reason": "clear", "outcome": "supported_value" if name in {"is_direct_quote", "quoted_speaker", "quotation_chain"} else "no_supported_value"} for name in quotation_fields},
    })
    assert populated.metadata.quoted_speaker == "Emmanuel Levinas"
    with pytest.raises(Exception):
        ms.response_model_for(schema, "quotation").model_validate({
            "metadata": {
                "is_direct_quote": True,
                "quoted_speaker": ["Emmanuel Levinas"],
                **{name: None for name in scalar_quotation_fields if name != "quoted_speaker"},
                "quotation_chain": [],
            },
            "field_assessments": {name: {"confidence": 0.9, "needs_review": False, "reason": "clear", "outcome": "supported_value" if name in {"is_direct_quote", "quoted_speaker"} else "no_supported_value"} for name in quotation_fields},
        })
    generated = ms.response_model_for(schema, "discourse").model_json_schema()
    assert "field_assessments" in generated["required"]


def custom():
    return ms.MetadataSchema(
        name="Reading notes", groups=[ms.SchemaGroup(key="discourse", label="Notes", intro="Read the record.", footer="Report {assessed_fields}.\n"),
                                       ms.SchemaGroup(key="ideas", label="Ideas", intro="List the ideas.")],
        fields=[
            ms.SchemaField(name="mood", label="Mood", type="choice", values=[ms.SchemaValue(value="calm", definition="Even in tone."), ms.SchemaValue(value="angry")], strict=True,
                           instruction="is the emotional register. One of: {values}", assess=True, evidence=True),
            ms.SchemaField(name="ideas", label="Ideas", type="list", group="ideas"),
            ms.SchemaField(name="year_mentioned", label="Year mentioned", type="number", group="ideas"),
        ],
    )


def test_retrieval_profile_migrates_abandoned_routing_fields_without_losing_metadata_disable():
    profile = ms.RetrievalProfile.model_validate(
        {
            "enabled": True,
            "scope": "all_reviewed",
            "max_items": 4,
            "min_similarity": 0.35,
            "include_corrections": False,
            "include_confirmed_absence": True,
            "use_for_metadata_enrichment": False,
            "use_for_response_memory": True,
            "use_for_claim_memory": True,
        }
    )

    assert profile.enabled is False
    assert profile.max_items == 4
    assert profile.min_similarity == 0.35
    dumped = profile.model_dump(mode="json")
    assert set(dumped) == {
        "enabled",
        "max_items",
        "min_similarity",
        "include_corrections",
        "include_confirmed_absence",
        "max_corrections",
        "match_field_ids",
    }


def test_a_custom_schema_shapes_the_prompt_and_the_answer():
    schema = custom()
    text = prompt(schema, "discourse")
    assert '- mood is the emotional register. One of: ["calm", "angry"]' in text
    assert 'Operational mood values definitions:\n{"calm": "Even in tone."}' in text
    assert "Report region_type, primary_text, discourse_role, and mood.\n" in text  # the locked core is always assessed
    assert prompt(schema, "ideas").startswith("List the ideas.\n\n<<CONTEXT>>")
    model = ms.response_model_for(schema, "discourse")
    assessments = {name: {"confidence": 0.9, "needs_review": False, "reason": "clear", "outcome": "supported_value"} for name in ("region_type", "primary_text", "discourse_role", "mood")}
    evidence = {name: {"block_ids": ["b1"], "confidence": 0.9, "reason": "clear"} for name in ("region_type", "primary_text", "discourse_role", "mood")}
    ok = model.model_validate({"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", "mood": "calm"}, "field_assessments": assessments, "field_evidence": evidence})
    assert ok.metadata.mood == "calm"
    with pytest.raises(Exception):
        model.model_validate({"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", "mood": "furious"}, "field_assessments": assessments, "field_evidence": evidence})  # strict values
    with pytest.raises(Exception):
        model.model_validate({"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", "mood": "calm"}})
    bad_assessment = {**assessments, "mood": {"needs_review": False, "reason": "clear", "outcome": "supported_value"}}
    with pytest.raises(Exception):
        model.model_validate({"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", "mood": "calm"}, "field_assessments": bad_assessment, "field_evidence": evidence})
    ideas = ms.response_model_for(schema, "ideas").model_validate({"metadata": {"ideas": ["hospitality"], "year_mentioned": 1795.0}})
    assert ideas.metadata.year_mentioned == 1795.0


@pytest.mark.parametrize("bad, message", [
    (dict(name="region_type"), "used by DerridAI"),
    (dict(name="Bad Name"), "lower-case"),
    (dict(name="page_start"), "used by DerridAI"),
    (dict(name="okname", type="choice"), "at least one allowed value"),
    (dict(name="okname", type="text", values=[{"value": "x"}]), "Only a choice field"),
    (dict(name="okname", group="nowhere"), "does not have"),
])
def test_a_schema_cannot_use_the_locked_core_or_break_its_own_rules(bad, message):
    base = custom().model_dump(mode="json")
    base["fields"] = [{**ms.SchemaField(name="ok_field", label="X").model_dump(mode="json"), **bad}]
    with pytest.raises(Exception) as exc:
        ms.MetadataSchema.model_validate(base)
    assert message in str(exc.value)


def test_a_schema_needs_the_discourse_group_and_unique_names():
    with pytest.raises(Exception, match="discourse"):
        ms.MetadataSchema(name="x", groups=[ms.SchemaGroup(key="other", label="O", intro="i")])
    with pytest.raises(Exception, match="different from each other"):
        ms.MetadataSchema(name="x", groups=[ms.SchemaGroup(key="discourse", label="D", intro="i")],
                          fields=[ms.SchemaField(name="dup_a", label="A"), ms.SchemaField(name="dup_a", label="B")])


def test_export_and_import_round_trip_and_reject_a_damaged_or_foreign_file():
    schema = custom()
    exported = ms.export_schema(schema)
    back = ms.import_schema(json.loads(json.dumps(exported)))
    assert back.content_hash() == schema.content_hash() and back.id == ""
    tampered = json.loads(json.dumps(exported))
    tampered["schema"]["fields"][0]["label"] = "Changed"
    with pytest.raises(ms.SchemaImportError, match="checksum"):
        ms.import_schema(tampered)
    with pytest.raises(ms.SchemaImportError, match="not a DerridAI"):
        ms.import_schema({"hello": 1})
    with pytest.raises(ms.SchemaImportError, match="format"):
        ms.import_schema({**exported, "derridai_metadata_schema": 99})
    broken = json.loads(json.dumps(exported)); broken["sha256"] = ""; broken["schema"]["fields"][0]["name"] = "region_type"
    with pytest.raises(ms.SchemaImportError, match="not valid"):
        ms.import_schema(broken)


def test_the_hash_ignores_the_id_but_not_the_content():
    a, b = custom(), custom()
    b.id = "something-else"
    assert a.content_hash() == b.content_hash()
    b.description = "different"
    assert a.content_hash() != b.content_hash()


# ---- the store ------------------------------------------------------------------------------------------------------

from app.metadata_schema_store import (  # noqa: E402
    SchemaLocked,
    SchemaNotFound,
    SchemaStore,
)


def test_builtin_schemas_are_first_and_cannot_be_changed_or_deleted(tmp_path):
    store = SchemaStore(tmp_path)
    listing = store.list()
    assert [item["id"] for item in listing[:3]] == ["default", "derridai-fiction", "derridai-nonfiction"]
    assert all(item["builtin"] is True for item in listing[:3])
    assert listing[0]["field_count"] >= 20
    for schema_id in BUILTIN_SCHEMA_IDS:
        with pytest.raises(SchemaLocked):
            store.save(custom(), schema_id)
        with pytest.raises(SchemaLocked):
            store.delete(schema_id)


def test_saving_gives_a_unique_id_and_survives_a_reload(tmp_path):
    store = SchemaStore(tmp_path)
    a = store.save(custom())
    b = store.save(custom())
    assert (a.id, b.id) == ("reading-notes", "reading-notes-2")
    again = SchemaStore(tmp_path).get("reading-notes")
    assert again.content_hash() == custom().content_hash() and again.id == "reading-notes"
    assert a.schema_version == "1.0.0"
    unchanged = store.save(custom(), "reading-notes")
    assert unchanged.schema_version == "1.0.0"
    updated = custom(); updated.description = "changed"
    changed = store.save(updated, "reading-notes")
    assert changed.schema_version == "1.0.1"
    added = custom()
    added.fields.append(ms.SchemaField(name="new_note", label="New note"))
    assert store.save(added, "reading-notes").schema_version == "1.1.0"
    removed = custom()
    removed.fields = [field for field in removed.fields if field.name != "mood"]
    assert store.save(removed, "reading-notes").schema_version == "2.0.0"
    assert store.get("reading-notes").description == ""
    store.delete("reading-notes-2")
    with pytest.raises(SchemaNotFound):
        store.get("reading-notes-2")
    with pytest.raises(SchemaNotFound):
        store.save(custom(), "never-saved")


def test_a_schema_named_like_the_built_in_never_takes_its_id(tmp_path):
    named = custom(); named.name = "Default"
    assert SchemaStore(tmp_path).save(named).id == "schema"


def test_import_goes_through_the_same_checks_and_a_bad_id_is_not_a_path(tmp_path):
    store = SchemaStore(tmp_path)
    saved = store.import_(ms.export_schema(custom()))
    assert store.get(saved.id).name == "Reading notes"
    with pytest.raises(ms.SchemaImportError):
        store.import_({"nope": 1})
    for evil in ("../etc/passwd", "a/b", ".hidden", ""):
        with pytest.raises(SchemaNotFound):
            store.get(evil)


def test_a_damaged_file_does_not_hide_the_others(tmp_path):
    store = SchemaStore(tmp_path)
    store.save(custom())
    (store.dir / "broken.json").write_text("{not json")
    assert [s["id"] for s in store.list()] == ["default", "derridai-fiction", "derridai-nonfiction", "reading-notes"]


def test_the_api_lists_saves_exports_imports_and_deletes(tmp_path, monkeypatch):
    import asyncio
    import sys
    import types

    import httpx

    try:
        import chromadb  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["chromadb"] = types.SimpleNamespace()
    from app import main
    from app.auth import auth_store
    from app.routers import corpus as corpus_routes

    monkeypatch.setattr(corpus_routes, "metadata_schemas", SchemaStore(tmp_path))
    monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: types.SimpleNamespace(id=1, role="admin", username="a"))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
            body = custom().model_dump(mode="json")
            created = (await c.post("/api/pdf/metadata-schemas", json=body)).json()
            listing = (await c.get("/api/pdf/metadata-schemas")).json()["items"]
            exported = await c.get(f"/api/pdf/metadata-schemas/{created['id']}/export")
            imported = await c.post("/api/pdf/metadata-schemas/import", json=exported.json())
            bad = await c.post("/api/pdf/metadata-schemas", json={**body, "fields": [{**body["fields"][0], "name": "region_type"}]})
            locked = await c.put("/api/pdf/metadata-schemas/default", json=body)
            gone = await c.delete(f"/api/pdf/metadata-schemas/{created['id']}")
            missing = await c.get("/api/pdf/metadata-schemas/nope")
            return created, listing, exported, imported, bad, locked, gone, missing

    created, listing, exported, imported, bad, locked, gone, missing = asyncio.run(run())
    assert created["id"] == "reading-notes" and [s["id"] for s in listing] == ["default", "derridai-fiction", "derridai-nonfiction", "reading-notes"]
    assert "attachment" in exported.headers["content-disposition"] and imported.json()["id"] == "reading-notes-2"
    assert bad.status_code == 422 and locked.status_code == 422 and gone.status_code == 200 and missing.status_code == 404


def test_the_preview_endpoint_shows_the_prompt_without_calling_a_model(tmp_path, monkeypatch):
    import asyncio
    import sys
    import types

    import httpx

    try:
        import chromadb  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["chromadb"] = types.SimpleNamespace()
    from app import main
    from app.auth import auth_store

    monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: types.SimpleNamespace(id=1, role="admin", username="a"))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
            good = await c.post("/api/pdf/metadata-schemas/preview", json={"schema": custom().model_dump(mode="json"), "group": "discourse", "text": "A calm passage."})
            bad = await c.post("/api/pdf/metadata-schemas/preview", json={"schema": custom().model_dump(mode="json"), "group": "nope", "text": "x"})
            return good, bad

    good, bad = asyncio.run(run())
    assert good.status_code == 200 and "A calm passage." in good.json()["prompt"] and good.json()["ran"] is False
    assert bad.status_code == 422


def test_researcher_cannot_author_metadata_schemas(tmp_path, monkeypatch):
    import asyncio
    import sys
    import types

    import httpx

    try:
        import chromadb  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["chromadb"] = types.SimpleNamespace()
    from app import main
    from app.auth import auth_store
    from app.routers import corpus as corpus_routes

    monkeypatch.setattr(corpus_routes, "metadata_schemas", SchemaStore(tmp_path))
    monkeypatch.setattr(
        auth_store,
        "user_for_session",
        lambda cookie: types.SimpleNamespace(id=2, role="researcher", username="r"),
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
            listing = await c.get("/api/pdf/metadata-schemas")
            created = await c.post("/api/pdf/metadata-schemas", json=custom().model_dump(mode="json"))
            return listing, created

    listing, created = asyncio.run(run())
    assert listing.status_code == 403 and created.status_code == 403



def test_metadata_schema_accepts_complete_supported_pos_and_ner_vocabularies():
    pos_tags = [
        "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN", "NUM",
        "PART", "PRON", "PROPN", "PUNCT", "SCONJ", "SYM", "VERB", "X",
    ]
    ner_tags = [
        "CARDINAL", "DATE", "EVENT", "FAC", "GPE", "LANGUAGE", "LAW", "LOC",
        "MONEY", "NORP", "ORDINAL", "ORG", "PERCENT", "PERSON", "PRODUCT",
        "QUANTITY", "TIME", "WORK_OF_ART",
    ]
    schema = MetadataSchema(
        name="NLP tags",
        groups=[
            SchemaGroup(
                key="core",
                label="Core",
                intro="Infer core metadata.",
            ),
            SchemaGroup(
                key="discourse",
                label="Discourse",
                intro="Infer discourse metadata.",
            ),
        ],
        fields=[
            SchemaField(
                name="entities",
                label="Entities",
                group="discourse",
                pos_tags=pos_tags,
                ner_tags=ner_tags,
            )
        ],
    )
    field = schema.fields[0]
    assert field.pos_tags == pos_tags
    assert field.ner_tags == ner_tags



def test_retrieval_match_conditions_must_name_another_known_field():
    base = custom().model_dump(mode="json")
    first, second = base["fields"][0], base["fields"][1]
    first["retrieval_profile"] = {"match_field_ids": [second["field_id"]]}
    assert MetadataSchema.model_validate(base).retrieval_profile_for(first["name"]).match_field_ids == [second["field_id"]]
    first["retrieval_profile"] = {"match_field_ids": ["field-does-not-exist"]}
    with pytest.raises(ValueError, match="unknown field"):
        MetadataSchema.model_validate(base)
    first["retrieval_profile"] = {"match_field_ids": [first["field_id"]]}
    with pytest.raises(ValueError, match="itself"):
        MetadataSchema.model_validate(base)



def test_boolean_false_is_supported_value_not_missing_value():
    schema = ms.default_schema()
    response = ms.response_model_for(schema, "quotation")
    quotation_fields = [field.name for field in schema.fields_in("quotation")]
    scalar_fields = [name for name in quotation_fields if name != "quotation_chain"]
    payload = {
        "metadata": {
            **{name: None for name in scalar_fields},
            "is_direct_quote": False,
            "quotation_chain": [],
        },
        "field_assessments": {
            name: {
                "confidence": 0.95,
                "needs_review": False,
                "reason": "No direct quotation is present.",
                "outcome": "no_supported_value",
            }
            for name in [field.name for field in schema.fields_in("quotation") if field.assess]
        },
        "field_evidence": {},
        "review_reason": "",
    }
    parsed = response.model_validate(payload)
    assert parsed.metadata.is_direct_quote is False
    assert parsed.field_assessments.is_direct_quote.outcome == "supported_value"
    assert "Structured-output contradiction" not in parsed.field_assessments.is_direct_quote.reason


def test_open_fields_reject_pos_ner_and_foreign_closed_vocabulary_leakage():
    schema = ms.default_schema()
    response = ms.response_model_for(schema, "quotation")
    quotation_fields = [field.name for field in schema.fields_in("quotation")]
    metadata = {name: None for name in quotation_fields if name != "quotation_chain"}
    metadata["quotation_chain"] = ["PROPN", "assertion", "Jacques Derrida"]
    assessments = {
        field.name: {
            "confidence": 0.8,
            "needs_review": False,
            "reason": "candidate",
            "outcome": "supported_value",
        }
        for field in schema.fields_in("quotation")
        if field.assess
    }
    payload = {
        "metadata": metadata,
        "field_assessments": assessments,
        "field_evidence": {},
        "review_reason": "",
    }
    parsed = response.model_validate(payload)
    assert parsed.metadata.quotation_chain == ["Jacques Derrida"]
    assert parsed.field_assessments.quotation_chain.outcome == "uncertain"
    assert parsed.field_assessments.quotation_chain.needs_review is True
    assert "structured-vocabulary leakage" in parsed.field_assessments.quotation_chain.reason

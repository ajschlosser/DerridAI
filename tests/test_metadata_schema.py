"""Metadata schemas: the built-in one reproduces today's prompts, and custom ones are validated and portable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app import metadata_schema as ms
from app.corpus_metadata import (
    ATTRIBUTION_EVIDENCE_FIELDS,
    METADATA_FAMILY_FIELDS,
    REVIEW_METADATA_FIELDS,
)

LEGACY = json.loads((Path(__file__).parent / "fixtures" / "legacy_prompts.json").read_text(encoding="utf-8"))
CONTEXT = "<<CONTEXT>>\n"


def prompt(schema, group):
    return ms.build_group_prompt(schema, group, base_context=CONTEXT)


def test_the_built_in_schema_reproduces_the_prompts_derridai_has_always_used():
    schema = ms.default_schema()
    # Quotation and indexing are identical. Discourse differs only in the order of two lines (stance before proposition
    # status, which is the order the assessments were always listed in).
    assert prompt(schema, "quotation") == LEGACY["quotation"]
    assert prompt(schema, "indexing") == LEGACY["indexing"]
    legacy = LEGACY["discourse"].split("\n")
    a = next(i for i, line in enumerate(legacy) if line.startswith("- proposition_status "))
    legacy[a], legacy[a + 1] = legacy[a + 1], legacy[a]
    assert prompt(schema, "discourse") == "\n".join(legacy)


def test_the_built_in_schema_describes_the_same_fields_as_the_code_does_today():
    schema = ms.default_schema()
    assert schema.family_fields() == {k: v - {"attribution_confidence", "semantic_classification_confidence"} for k, v in METADATA_FAMILY_FIELDS.items()}
    assert schema.attribution_fields() == set(ATTRIBUTION_EVIDENCE_FIELDS)
    assert set(schema.review_fields()) == set(REVIEW_METADATA_FIELDS)
    assert schema.review_fields()[:3] == list(ms.CORE_FIELDS)


def test_the_output_shape_is_generated_and_matches_the_hand_written_models():
    from app import corpus_builder as cb

    schema = ms.default_schema()
    for group, legacy in (("discourse", cb.DiscourseMetadataResponseModel), ("quotation", cb.QuotationMetadataResponseModel), ("indexing", cb.IndexMetadataResponseModel)):
        model = ms.response_model_for(schema, group)
        got = set(model.model_json_schema()["$defs"][f"{group.title()}Metadata"]["properties"])
        want = set(legacy.model_json_schema()["$defs"][legacy.model_fields["metadata"].annotation.__name__]["properties"])
        want -= {"language"}  # the document language is inherited, not asked of the model
        assert got == want, group
    answer = ms.response_model_for(schema, "quotation").model_validate({"metadata": {"is_direct_quote": None, **{n: [] for n in ("quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder", "quoted_addressee", "quoted_referent", "quotation_chain")}}})
    assert answer.metadata.is_direct_quote is None


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


def test_a_custom_schema_shapes_the_prompt_and_the_answer():
    schema = custom()
    text = prompt(schema, "discourse")
    assert '- mood is the emotional register. One of: ["calm", "angry"]' in text
    assert 'Operational mood values definitions:\n{"calm": "Even in tone."}' in text
    assert "Report region_type, primary_text, discourse_role, and mood.\n" in text  # the locked core is always assessed
    assert prompt(schema, "ideas").startswith("List the ideas.\n\n<<CONTEXT>>")
    model = ms.response_model_for(schema, "discourse")
    ok = model.model_validate({"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", "mood": "calm"}})
    assert ok.metadata.mood == "calm"
    with pytest.raises(Exception):
        model.model_validate({"metadata": {"region_type": "main_text", "primary_text": True, "discourse_role": "assertion", "mood": "furious"}})  # strict values
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


def test_the_built_in_schema_is_always_first_and_cannot_be_changed_or_deleted(tmp_path):
    store = SchemaStore(tmp_path)
    listing = store.list()
    assert listing[0]["id"] == "default" and listing[0]["builtin"] is True and listing[0]["field_count"] >= 20
    with pytest.raises(SchemaLocked):
        store.save(custom(), "default")
    with pytest.raises(SchemaLocked):
        store.delete("default")


def test_saving_gives_a_unique_id_and_survives_a_reload(tmp_path):
    store = SchemaStore(tmp_path)
    a = store.save(custom())
    b = store.save(custom())
    assert (a.id, b.id) == ("reading-notes", "reading-notes-2")
    again = SchemaStore(tmp_path).get("reading-notes")
    assert again.content_hash() == custom().content_hash() and again.id == "reading-notes"
    updated = custom(); updated.description = "changed"
    store.save(updated, "reading-notes")
    assert store.get("reading-notes").description == "changed"
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
    assert [s["id"] for s in store.list()] == ["default", "reading-notes"]


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

    monkeypatch.setattr(main, "metadata_schemas", SchemaStore(tmp_path))
    monkeypatch.setattr(main.auth_store, "user_for_session", lambda cookie: types.SimpleNamespace(id=1, role="admin", username="a"))

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
    assert created["id"] == "reading-notes" and [s["id"] for s in listing] == ["default", "reading-notes"]
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

    monkeypatch.setattr(main.auth_store, "user_for_session", lambda cookie: types.SimpleNamespace(id=1, role="admin", username="a"))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
            good = await c.post("/api/pdf/metadata-schemas/preview", json={"schema": custom().model_dump(mode="json"), "group": "discourse", "text": "A calm passage."})
            bad = await c.post("/api/pdf/metadata-schemas/preview", json={"schema": custom().model_dump(mode="json"), "group": "nope", "text": "x"})
            return good, bad

    good, bad = asyncio.run(run())
    assert good.status_code == 200 and "A calm passage." in good.json()["prompt"] and good.json()["ran"] is False
    assert bad.status_code == 422

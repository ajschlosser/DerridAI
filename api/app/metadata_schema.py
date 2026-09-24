# Copyright 2026 Aaron John Schlosser, PhD.
"""Metadata schemas: which fields a JSONL record has, what each may hold, and what the model is told to look for.

A schema is data. It describes groups of fields (each group is one model call per record) and the fields in them, with a
field's type, its allowed values and the instruction the model receives. The three fields that DerridAI's own logic
depends on (region type, primary text, discourse role) are the locked core: every schema has them, in the "discourse"
group, and a schema cannot change or remove them. Everything else is the schema's to define.

The built-in schema, `default_schema()`, describes exactly the fields and instructions DerridAI has always used, so
choosing it changes nothing. A build takes a copy of its schema when it starts and never reads the saved one again, so
editing or deleting a saved schema cannot alter a build that used it.

Schemas are exported as one JSON file with a format version and a content hash, and imported through the same
validation as anything typed into an editor.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    field_validator,
    model_validator,
)

from .corpus_metadata import (
    ATTRIBUTION_EVIDENCE_FIELDS,
    DISCOURSE_ROLE_DEFINITIONS,
    DISCOURSE_ROLES,
    MANIFEST_INHERITED_FIELDS,
    PROPOSITION_STATUS_VALUES,
    REGION_TYPES,
    REVIEW_METADATA_FIELDS,
    SOURCE_BOUND_FIELDS,
    STANCE_VALUES,
)

FORMAT_VERSION = 1
DEFAULT_SCHEMA_ID = "default"
CORE_FIELDS = ("region_type", "primary_text", "discourse_role")
CORE_GROUP = "discourse"
# Names a schema may not use: the core, the record's own source fields, the document-level fields records inherit, and
# fields DerridAI computes itself.
RESERVED_NAMES = (
    set(CORE_FIELDS) | set(SOURCE_BOUND_FIELDS) | set(MANIFEST_INHERITED_FIELDS)
    | {"language", "needs_review", "review_reason", "attribution_confidence", "semantic_classification_confidence", "extraction_quality",
       "inline_citation", "full_citation", "metadata", "field_evidence", "field_assessments"}
)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_FIELDS = 60
MAX_GROUPS = 6

FieldType = Literal["text", "number", "boolean", "choice", "list"]
RetrievalScope = Literal["same_schema", "same_field", "all_reviewed"]


class RetrievalProfile(BaseModel):
    """Declarative policy for which reviewed memory may guide a field.

    This is configuration, not a retrieval result.  Scores, ranks, and
    provider-specific diagnostics therefore never become part of a schema.
    """

    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    scope: RetrievalScope = "same_field"
    max_items: int = Field(default=6, ge=0, le=50)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    include_corrections: bool = True
    include_confirmed_absence: bool = True
    use_for_metadata_enrichment: bool = True
    use_for_response_memory: bool = False
    use_for_claim_memory: bool = False


class SchemaValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1, max_length=80)
    definition: str = Field(default="", max_length=600)


class SchemaField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = ""
    name: str
    semantic_compatibility_id: str | None = Field(default=None, max_length=120)
    label: str = Field(min_length=1, max_length=80)
    type: FieldType = "text"
    group: str = "discourse"
    # For "choice": the allowed values. `strict` makes them the only values the model may return; otherwise they are
    # what it is told to prefer, and a person may still type another.
    values: list[SchemaValue] = Field(default_factory=list, max_length=60)
    strict: bool = False
    # The model is told this, after the field's name, in the group's list of fields. "{values}" is replaced by the allowed values.
    instruction: str = Field(default="", max_length=1500)
    definitions_heading: str = Field(default="", max_length=120)
    evidence: bool = False  # the model must cite source blocks for a value
    assess: bool = False  # the model must report its confidence
    review: bool = False  # an unresolved value here keeps a record out of "accepted" until a person decides
    retrieval_profile: RetrievalProfile | None = None

    @model_validator(mode="before")
    @classmethod
    def _identity_defaults(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        name = str(result.get("name") or "").strip()
        if not str(result.get("field_id") or "").strip() and name:
            # Deterministic migration for format-v1 schemas.  A deliberate
            # rename can retain identity by sending the previous field_id.
            result["field_id"] = f"field-{uuid.uuid5(uuid.NAMESPACE_URL, 'derridai:field:' + name)}"
        return result

    @field_validator("field_id")
    @classmethod
    def _field_id(cls, value: str) -> str:
        if not value:
            raise ValueError("A field needs a stable field_id.")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{1,119}", value):
            raise ValueError("field_id must be a stable identifier.")
        return value

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not NAME_RE.match(value):
            raise ValueError("A field name is lower-case letters, digits and underscores, starting with a letter (2 to 40 characters).")
        if value in RESERVED_NAMES:
            raise ValueError(f"'{value}' is used by DerridAI itself and cannot be a field name.")
        return value

    @model_validator(mode="after")
    def _choice(self) -> SchemaField:
        if self.type == "choice" and not self.values:
            raise ValueError("A choice field needs at least one allowed value.")
        if self.type != "choice" and (self.values or self.strict):
            raise ValueError("Only a choice field has allowed values.")
        seen = [v.value for v in self.values]
        if len(seen) != len(set(seen)):
            raise ValueError("Allowed values must be different from each other.")
        return self


class SchemaGroup(BaseModel):
    """One model call per record: the opening text, the notes after the field list, and the closing instructions."""

    model_config = ConfigDict(extra="forbid")
    key: str
    label: str = Field(min_length=1, max_length=80)
    intro: str = Field(min_length=1, max_length=4000)
    fields_heading: str = Field(default="", max_length=200)
    notes: list[str] = Field(default_factory=list, max_length=12)
    trailer: str = Field(default="", max_length=4000)
    # May use {fields} (this group's field names) and {assessed_fields} (the ones the model reports confidence for).
    footer: str = Field(default="", max_length=4000)
    retrieval_profile: RetrievalProfile | None = None

    @field_validator("key")
    @classmethod
    def _key(cls, value: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]{1,23}$", value):
            raise ValueError("A group key is lower-case letters, digits and underscores (2 to 24 characters).")
        return value


class MetadataSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format_version: int = FORMAT_VERSION
    schema_version: str = "1.0.0"
    id: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=600)
    groups: list[SchemaGroup] = Field(max_length=MAX_GROUPS)
    fields: list[SchemaField] = Field(default_factory=list, max_length=MAX_FIELDS)

    @field_validator("schema_version")
    @classmethod
    def _schema_version(cls, value: str) -> str:
        if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
            raise ValueError("Schema version must use semantic versioning, for example 1.0.0.")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> MetadataSchema:
        keys = [g.key for g in self.groups]
        if len(keys) != len(set(keys)):
            raise ValueError("Group keys must be different from each other.")
        if CORE_GROUP not in keys:
            raise ValueError(f"A schema needs the '{CORE_GROUP}' group: it holds the locked core fields.")
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be different from each other.")
        ids = [f.field_id for f in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("Field identities must be different from each other.")
        for field in self.fields:
            if field.group not in keys:
                raise ValueError(f"Field '{field.name}' is in a group ('{field.group}') the schema does not have.")
        return self

    # ---- what the rest of DerridAI asks a schema ----------------------------------------------------------------
    def group(self, key: str) -> SchemaGroup:
        return next(g for g in self.groups if g.key == key)

    def fields_in(self, key: str) -> list[SchemaField]:
        return [f for f in self.fields if f.group == key]

    def field_names(self) -> list[str]:
        return list(CORE_FIELDS) + [f.name for f in self.fields]

    def field_id(self, name: str) -> str:
        """Return the stable identity used by memory bindings and migrations."""
        if name in CORE_FIELDS:
            return f"core.{name}"
        field = next((item for item in self.fields if item.name == name), None)
        if field is None:
            raise KeyError(name)
        return field.field_id

    def field_identity_map(self) -> dict[str, str]:
        return {name: self.field_id(name) for name in self.field_names()}

    def retrieval_profile_for(self, name: str) -> RetrievalProfile:
        """Resolve field policy, falling back to its group and then defaults."""
        if name in CORE_FIELDS:
            group = self.group(CORE_GROUP)
            return group.retrieval_profile or RetrievalProfile()
        field = next((item for item in self.fields if item.name == name), None)
        if field is None:
            raise KeyError(name)
        if field.retrieval_profile is not None:
            return field.retrieval_profile
        return self.group(field.group).retrieval_profile or RetrievalProfile()

    def family_fields(self) -> dict[str, set[str]]:
        """Group key to its field names; the core sits in its group. Same shape as METADATA_FAMILY_FIELDS."""
        out = {g.key: {f.name for f in self.fields_in(g.key)} for g in self.groups}
        out[CORE_GROUP] |= set(CORE_FIELDS)
        return out

    def evidence_fields(self) -> set[str]:
        return {f.name for f in self.fields if f.evidence} | set(CORE_FIELDS)

    def attribution_fields(self) -> set[str]:
        return {f.name for f in self.fields if f.evidence}

    def review_fields(self) -> list[str]:
        return list(CORE_FIELDS) + [f.name for f in self.fields if f.review]

    def by_name(self) -> dict[str, SchemaField]:
        return {f.name: f for f in self.fields}

    def content_hash(self) -> str:
        body = self.model_dump(mode="json", exclude={"id"})
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


# ---- export and import --------------------------------------------------------------------------------------------

def export_schema(schema: MetadataSchema) -> dict[str, Any]:
    body = schema.model_dump(mode="json", exclude={"id"})
    return {"derridai_metadata_schema": FORMAT_VERSION, "sha256": schema.content_hash(), "schema": body}


class SchemaImportError(ValueError):
    pass


def import_schema(payload: Any) -> MetadataSchema:
    """Validate an exported schema. The hash catches a file edited or damaged after export; it is not a signature."""
    if not isinstance(payload, dict) or "derridai_metadata_schema" not in payload or not isinstance(payload.get("schema"), dict):
        raise SchemaImportError("This is not a DerridAI metadata schema file.")
    if payload["derridai_metadata_schema"] != FORMAT_VERSION:
        raise SchemaImportError(f"This schema file is format {payload['derridai_metadata_schema']}; this DerridAI reads format {FORMAT_VERSION}.")
    try:
        schema = MetadataSchema.model_validate({**payload["schema"], "id": ""})
    except ValidationError as exc:
        raise SchemaImportError("The schema is not valid: " + "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5])) from exc
    if payload.get("sha256"):
        current_hash = schema.content_hash()
        # Format version 1 predates stable field IDs and retrieval profiles.
        # Accept the exact legacy body hash while migrating it in memory.
        raw_body = {key: value for key, value in payload["schema"].items() if key != "id"}
        legacy_hash = hashlib.sha256(
            json.dumps(raw_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        if payload["sha256"] not in {current_hash, legacy_hash}:
            raise SchemaImportError("The file's contents do not match its checksum: it was edited or damaged after it was exported.")
    return schema


# ---- prompts --------------------------------------------------------------------------------------------------------

def _oxford(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + (", and " if len(names) > 2 else " and ") + names[-1]


def _values_json(field: SchemaField) -> str:
    return json.dumps([v.value for v in field.values], ensure_ascii=False)


def build_group_prompt(
    schema: MetadataSchema, group_key: str, *, base_context: str,
    allowed_region_types: list[str] | None = None, allowed_discourse_roles: list[str] | None = None,
) -> str:
    """The prompt for one group, in the same shape DerridAI has always used:

    opening text, the list of fields with their instructions, notes, definitions of any values that have them, closing
    remarks, the shared context block, then the evidence and assessment instructions.
    """
    group = schema.group(group_key)
    fields = schema.fields_in(group_key)
    region_types = allowed_region_types or REGION_TYPES
    roles = allowed_discourse_roles or DISCOURSE_ROLES
    lines: list[str] = []
    definitions: list[tuple[str, dict[str, str]]] = []
    if group_key == CORE_GROUP:
        lines += [
            f"- region_type MUST be one of: {json.dumps(region_types, ensure_ascii=False)}",
            f"- discourse_role MUST be one of: {json.dumps(roles, ensure_ascii=False)}",
            "- primary_text MUST be true or false. It means the record belongs to the substantive work rather than front/back matter, "
            "bibliography, index, publishing paratext, or other apparatus.",
        ]
        definitions.append(("discourse-role", {role: DISCOURSE_ROLE_DEFINITIONS.get(role, "") for role in roles}))
    for field in fields:
        if field.instruction.strip():
            lines.append(f"- {field.name} " + field.instruction.strip().replace("{values}", _values_json(field)))
        described = {v.value: v.definition for v in field.values if v.definition}
        if described:
            definitions.append((field.definitions_heading or f"{field.name} values", described))
    lines += [f"- {note}" for note in group.notes]

    parts = [group.intro.rstrip()]
    if lines:
        parts.append((group.fields_heading.rstrip() + "\n" if group.fields_heading else "") + "\n".join(lines))
    for heading, mapping in definitions:
        parts.append(f"Operational {heading} definitions:\n{json.dumps(mapping, ensure_ascii=False)}")
    if group.trailer.strip():
        parts.append(group.trailer.strip())
    assessed = (list(CORE_FIELDS) if group_key == CORE_GROUP else []) + [f.name for f in fields if f.assess]
    footer = group.footer.replace("{fields}", _oxford(([*CORE_FIELDS] if group_key == CORE_GROUP else []) + [f.name for f in fields])).replace("{assessed_fields}", _oxford(assessed))
    return "\n\n".join(parts) + "\n\n" + base_context + "\n" + footer


# ---- the model's answer, generated from the schema ----------------------------------------------------------------

class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str = ""


AssessmentOutcome = Literal["supported_value", "no_supported_value", "uncertain"]


class FieldAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The key is required even when the model explicitly cannot estimate a
    # confidence.  ``null`` therefore means "reported unavailable", while an
    # omitted key is a structured-output failure that should be retried.
    confidence: float | None = Field(ge=0.0, le=1.0)
    needs_review: bool
    reason: str = Field(max_length=500)
    outcome: AssessmentOutcome


class MetadataResponseBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessed_fields_for_validation: ClassVar[tuple[str, ...]] = ()
    evidence_fields_for_validation: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def validate_metadata_assessment_consistency(self) -> MetadataResponseBase:
        metadata_obj = getattr(self, "metadata", None)
        metadata = metadata_obj.model_dump() if isinstance(metadata_obj, BaseModel) else dict(metadata_obj or {})
        assessments_obj = getattr(self, "field_assessments", None)
        assessments = assessments_obj.model_dump() if isinstance(assessments_obj, BaseModel) else dict(assessments_obj or {})
        evidence_obj = getattr(self, "field_evidence", None)
        if isinstance(evidence_obj, BaseModel):
            evidence = evidence_obj.model_dump()
        else:
            evidence = {
                str(key): value.model_dump() if isinstance(value, BaseModel) else value
                for key, value in dict(evidence_obj or {}).items()
            }

        def missing(value: Any) -> bool:
            return value is None or value == "" or value == []

        for field in self.assessed_fields_for_validation:
            assessment = assessments.get(field)
            if not isinstance(assessment, dict):
                continue
            value = metadata.get(field)
            outcome = str(assessment.get("outcome") or "")
            needs_review = bool(assessment.get("needs_review"))

            if outcome == "supported_value" and missing(value):
                raise ValueError(f"{field}: outcome=supported_value requires a non-empty metadata value")
            if outcome == "no_supported_value" and not missing(value):
                raise ValueError(f"{field}: outcome=no_supported_value requires an empty metadata value")
            if outcome == "uncertain" and not needs_review:
                raise ValueError(f"{field}: outcome=uncertain requires needs_review=true")

            if outcome == "supported_value" and field in self.evidence_fields_for_validation:
                info = evidence.get(field)
                block_ids = info.get("block_ids") if isinstance(info, dict) else None
                if not block_ids:
                    raise ValueError(
                        f"{field}: supported evidence-bearing values require at least one field_evidence block_id"
                    )
        return self


def _annotation(field: SchemaField) -> Any:
    if field.type == "boolean":
        return bool | None
    if field.type == "number":
        return float | None
    if field.type == "list":
        return Annotated[list[str], Field(max_length=24)]
    if field.type == "choice" and field.strict:
        return Literal[tuple(v.value for v in field.values)] | None
    return str | None


def response_model_for(schema: MetadataSchema, group_key: str, *, region_types: list[str] | None = None, roles: list[str] | None = None) -> type[BaseModel]:
    """The JSON shape the model must return for one group.

    Metadata keys are required (null/[] when unsupported), and every field the
    schema marks for assessment has a required assessment object.  This keeps
    prose instructions and the provider-enforced JSON Schema in agreement.
    """
    props: dict[str, Any] = {}
    if group_key == CORE_GROUP:
        props["region_type"] = (Literal[tuple(region_types or REGION_TYPES)] | None, ...)
        props["primary_text"] = (bool | None, ...)
        props["discourse_role"] = (Literal[tuple(roles or DISCOURSE_ROLES)] | None, ...)
    group_fields = schema.fields_in(group_key)
    for field in group_fields:
        props[field.name] = (_annotation(field), ...)
    metadata = create_model(f"{group_key.title()}Metadata", __config__=ConfigDict(extra="forbid"), **props)

    assessed_names = list(CORE_FIELDS) if group_key == CORE_GROUP else []
    assessed_names.extend(field.name for field in group_fields if field.assess)
    assessed_names = list(dict.fromkeys(assessed_names))

    fields: dict[str, Any] = {
        "metadata": (metadata, ...),
        "review_reason": (str, Field(default="", max_length=1000)),
    }
    if assessed_names:
        assessment_props: dict[str, Any] = {
            name: (FieldAssessment, ...) for name in assessed_names
        }
        assessments = create_model(
            f"{group_key.title()}FieldAssessments",
            __config__=ConfigDict(extra="forbid"),
            **assessment_props,
        )
        fields["field_assessments"] = (assessments, ...)
    else:
        # A custom family may intentionally contain no assessed fields.
        fields["field_assessments"] = (dict[str, FieldAssessment], Field(default_factory=dict))
    evidence_names = set(CORE_FIELDS) if group_key == CORE_GROUP else set()
    evidence_names.update(field.name for field in group_fields if field.evidence)
    if evidence_names:
        fields["field_evidence"] = (dict[str, FieldEvidence], Field(default_factory=dict))

    response = create_model(
        f"{group_key.title()}MetadataResponse",
        __base__=MetadataResponseBase,
        **fields,
    )
    response.assessed_fields_for_validation = tuple(assessed_names)
    response.evidence_fields_for_validation = tuple(sorted(evidence_names))
    return response


# ---- the built-in schema ------------------------------------------------------------------------------------------

_DISCOURSE_INTRO = (
    "Infer ONLY discourse/attribution metadata for one immutable DerridAI record.\n"
    "Distinguish the grammatical/textual speaker from the POSITION HOLDER whose proposition is being presented. A named person is not "
    "automatically a speaker or position holder. Preserve modality, negation, uncertainty, and stance. Do not return quotation relations, "
    "topical indexing, bibliographic metadata, summaries, or source text."
)
_DISCOURSE_NOTES = [
    "Independently assess region_type and primary_text even when deterministic document-structure metadata already exists. Return the "
    "semantically supported value and confidence. DerridAI will retain reviewer-defined structural facts as authoritative while recording any "
    "disagreement for review; do not suppress a disagreement merely because structure metadata exists.",
    "For target, claim_scope, speaker, position_holder, and related referenced entities, prefer short named entities or noun phrases, not full "
    "sentences or explanatory clauses. Example: target=\"cities of refuge\" is correct; target=\"The concept and practice of 'cities of refuge' as "
    "a form of cosmopolitics distinct from state sovereignty.\" is not acceptable.",
]
_DISCOURSE_TRAILER = (
    "For discourse_role, explicitly discriminate among the two or three closest plausible roles before choosing. In the discourse_role field "
    "assessment reason, briefly state why the selected role fits better than its nearest alternative. Pay special attention to the difference "
    "between the surrounding author's analysis and a reported_position held by someone else, and between critique, qualification, and commentary. "
    "Human-confirmed examples above are style/taxonomy guidance, not evidence.\n"
    "If a field is genuinely unsupported, return null rather than inventing a value. Never answer with a placeholder or a description of a role "
    "(\"null\", \"N/A\", \"unknown\", \"the author of the current record\", \"the speaker\", \"this passage\"): name the person, work or concept the "
    "text itself names, or return null."
)
_DISCOURSE_FOOTER = (
    "For every populated attribution-bearing field and every populated hybrid field (region_type, primary_text, discourse_role), include "
    "field_evidence using only current-record block IDs, confidence 0..1, and a short reason. Use null or [] when unsupported.\n"
    "Return one field_assessments entry for every one of {assessed_fields}, even when its metadata value is null or empty. Each assessment "
    "must contain all four keys: confidence (a number 0..1, or null only when confidence genuinely cannot be estimated), needs_review, reason, "
    "and outcome. Use outcome=\"supported_value\" when the returned value is supported, outcome=\"no_supported_value\" when the "
    "source supports that no value applies, and outcome=\"uncertain\" when the field cannot be determined. Mark needs_review=true whenever "
    "a proposed value or supported absence is genuinely ambiguous, attribution is uncertain, evidence is weak, or confidence is not sufficient "
    "for scholarly acceptance.\n"
)
_QUOTATION_INTRO = (
    "Infer ONLY quotation relations for one immutable DerridAI record.\n"
    "Determine whether there is direct quotation and, only when source-supported, identify quoted speaker/author/work/position-holder/addressee/"
    "referent and quotation chains. A mentioned name is not automatically a quoted source. Do not return discourse fields, topical indexing, "
    "bibliographic metadata, summaries, or source text."
)
_QUOTATION_FOOTER = (
    "For every populated quoted_* or quotation_chain field, include field_evidence using only current-record block IDs, confidence 0..1, and a "
    "short reason. Use [] when unsupported.\n"
    "Return one field_assessments entry for every one of {assessed_fields}, even when its metadata value is null or empty. Each assessment must "
    "contain confidence (0..1 or null), needs_review, reason, and outcome. Use outcome=\"supported_value\", "
    "outcome=\"no_supported_value\", or outcome=\"uncertain\" according to the source evidence.\n"
)
_INDEXING_INTRO = (
    "Infer ONLY conservative semantic indexing metadata for one immutable DerridAI record.\n"
    "Return topics, concepts, persons, and works_referenced that are materially present in this record. Do not infer discourse attribution, "
    "quotation ownership, bibliography, summaries, or source text. Prefer a short precise list to speculative coverage; emit brief noun phrases "
    "or proper names, not full sentences or explanatory clauses. Example: concepts=[\"cities of refuge\"] is acceptable; concepts=[\"The concept "
    "and practice of 'cities of refuge' as a form of cosmopolitics distinct from state sovereignty.\"] is not."
)
_INDEXING_FOOTER = (
    "Return one field_assessments entry for every one of {assessed_fields}, even when the corresponding metadata list is empty. Each assessment "
    "must contain confidence (0..1 or null), needs_review, reason, and outcome. Use outcome=\"supported_value\" for a supported non-empty "
    "list, outcome=\"no_supported_value\" when the record supports an empty list, and outcome=\"uncertain\" when the field cannot be "
    "determined.\n"
)


def _f(name: str, label: str, type_: FieldType, group: str, **kw: Any) -> SchemaField:
    return SchemaField(
        name=name, label=label, type=type_, group=group,
        evidence=name in ATTRIBUTION_EVIDENCE_FIELDS, review=name in REVIEW_METADATA_FIELDS, **kw,
    )


def default_schema() -> MetadataSchema:
    """The fields and instructions DerridAI has always used."""
    values = lambda items: [SchemaValue(value=v) for v in items]  # noqa: E731
    fields = [
        _f("region_author", "Region author", "text", "discourse"),
        _f("speaker", "Speaker", "text", "discourse", assess=True),
        _f("position_holder", "Position holder", "text", "discourse", assess=True),
        _f("target", "Target", "text", "discourse", assess=True),
        _f("stance", "Stance", "choice", "discourse", assess=True, values=values(STANCE_VALUES),
           instruction="describes the position holder's orientation toward the target/proposition. Prefer one of: {values}"),
        _f("proposition_status", "Proposition status", "choice", "discourse", assess=True, values=values(PROPOSITION_STATUS_VALUES),
           instruction="describes the character/status of the proposition, not a boolean. Prefer one of: {values}"),
        _f("claim_scope", "Claim scope", "text", "discourse", assess=True),
        _f("semantic_function", "Semantic function", "list", "discourse"),
        _f("is_direct_quote", "Direct quotation", "boolean", "quotation", assess=True),
        *[_f(n, lab, "list", "quotation", assess=True) for n, lab in (
            ("quoted_speaker", "Quoted speaker"), ("quoted_author", "Quoted author"), ("quoted_work", "Quoted work"),
            ("quoted_position_holder", "Quoted position holder"), ("quoted_addressee", "Quoted addressee"),
            ("quoted_referent", "Quoted referent"), ("quotation_chain", "Quotation chain"))],
        *[_f(n, lab, "list", "indexing", assess=True) for n, lab in (
            ("topics", "Topics"), ("concepts", "Concepts"), ("persons", "Persons"), ("works_referenced", "Works referenced"))],
    ]
    return MetadataSchema(
        id=DEFAULT_SCHEMA_ID, name="DerridAI scholarly default",
        description="Discourse and attribution, quotation relations, and semantic indexing: the fields DerridAI has always produced.",
        groups=[
            SchemaGroup(key="discourse", label="Discourse and attribution", intro=_DISCOURSE_INTRO, fields_heading="Hybrid classification fields are constrained:",
                        notes=_DISCOURSE_NOTES, trailer=_DISCOURSE_TRAILER, footer=_DISCOURSE_FOOTER),
            SchemaGroup(key="quotation", label="Quotation", intro=_QUOTATION_INTRO, footer=_QUOTATION_FOOTER),
            SchemaGroup(key="indexing", label="Semantic indexing", intro=_INDEXING_INTRO, footer=_INDEXING_FOOTER),
        ],
        fields=fields,
    )


def edit_model(schema: MetadataSchema, base: type[BaseModel]) -> type[BaseModel]:
    """What a person may enter when editing a record: the fixed editable fields, plus this schema's, checked by type.

    `base` is the record-metadata model of the fixed fields. The fields the default schema defines are removed from it,
    so a schema that leaves one out cannot have it set.
    """
    configurable = {f.name for f in default_schema().fields}
    props: dict[str, Any] = {name: (info.annotation, info) for name, info in base.model_fields.items() if name not in configurable}
    for field in schema.fields:
        annotation = _annotation(field)
        if field.type == "list":
            annotation = list[str]
        props[field.name] = (annotation | None if field.type != "list" else annotation, Field(default_factory=list) if field.type == "list" else None)
    return create_model("RecordEdit", __config__=ConfigDict(extra="forbid"), **props)

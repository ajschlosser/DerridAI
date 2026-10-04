# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Metadata schemas: which fields a JSONL record has, what each may hold, and what the model is told to look for.

A schema is data. It describes groups of fields (each group is one model call per record) and the fields in them, with a
field's type, its allowed values and the instruction the model receives. The three fields that DerridAI's own logic
depends on (region type, primary text, discourse role) are the locked core: every schema has them, in the "discourse"
group, and a schema cannot change or remove them. Everything else is the schema's to define.

The built-in schema, `default_schema()`, preserves DerridAI's historical scholarly field identities while expressing
their current value contracts explicitly. Historical storage shapes are compatibility inputs, not the authority for
field cardinality. Additional built-in domain profiles are registered in
`metadata_schema_profiles`; they use this same generic contract rather than adding domain-specific runtime branches.
A build takes a copy of its schema when it starts and never reads the saved one again, so editing or deleting a saved
schema cannot alter a build that used it.

Schemas are exported as one JSON file with a format version and a content hash, and imported through the same
validation as anything typed into an editor.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    AfterValidator,
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
from .semantic_identity import CollectionSemantics, EquivalenceMode, EquivalenceProfile

__all__ = ["CollectionSemantics", "EquivalenceMode", "EquivalenceProfile"]

# Format 2 replaced SchemaField.applies_to_work with `scope` and added `document_fields`.
# Format 3 adds stable list-of-object values for repeatable associated groups. Older files still import.
FORMAT_VERSION = 3
READABLE_FORMAT_VERSIONS = {1, 2, 3}
DEFAULT_SCHEMA_ID = "default"
CORE_FIELDS = ("region_type", "primary_text", "discourse_role")
CORE_GROUP = "discourse"
SEMANTIC_COMPATIBILITY_IDS = {
    "region_type": "derridai.region_type",
    "primary_text": "derridai.primary_text",
    "discourse_role": "derridai.discourse_role",
    "speaker": "derridai.speaker",
    "position_holder": "derridai.position_holder",
    "target": "derridai.target",
    "stance": "derridai.stance",
    "proposition_status": "derridai.proposition_status",
    "claim_scope": "derridai.claim_scope",
    "quoted_speaker": "derridai.quotation.speaker",
    "quoted_author": "derridai.quotation.author",
    "quoted_work": "derridai.quotation.work",
    "quoted_position_holder": "derridai.quotation.position_holder",
    "quoted_addressee": "derridai.quotation.addressee",
    "quoted_referent": "derridai.quotation.referent",
    "quotation_chain": "derridai.quotation.chain",
    "topics": "derridai.indexing.topics",
    "concepts": "derridai.indexing.concepts",
    "persons": "derridai.indexing.persons",
    "works_referenced": "derridai.indexing.works_referenced",
}
# Value-matching policy for DerridAI's own field semantics, keyed by stable semantic identity
# (never by display or storage name). A field's explicit ``equivalence_profile`` wins; otherwise
# these apply, and then a type-based fallback. Person-bearing fields share the ``person`` kind,
# so a speaker and an indexed person resolve to one identity.
DEFAULT_EQUIVALENCE_PROFILES: dict[str, EquivalenceProfile] = {
    **{
        compat: EquivalenceProfile(mode="entity_name", identity_kind="person")
        for compat in (
            "derridai.speaker", "derridai.position_holder", "derridai.quotation.speaker",
            "derridai.quotation.author", "derridai.quotation.position_holder",
            "derridai.quotation.addressee", "derridai.indexing.persons",
        )
    },
    "derridai.quotation.work": EquivalenceProfile(mode="text", identity_kind="work"),
    "derridai.indexing.works_referenced": EquivalenceProfile(mode="text", identity_kind="work"),
    "derridai.indexing.concepts": EquivalenceProfile(mode="lexical_phrase", identity_kind="concept"),
    "derridai.indexing.topics": EquivalenceProfile(mode="lexical_phrase", identity_kind="topic"),
    # A quotation chain is a sequence: who quotes whom is carried by order.
    "derridai.quotation.chain": EquivalenceProfile(mode="text", collection_semantics="ordered"),
    "derridai.region_type": EquivalenceProfile(mode="controlled"),
    "derridai.discourse_role": EquivalenceProfile(mode="controlled"),
    "derridai.primary_text": EquivalenceProfile(mode="exact"),
}

# Names a schema may not use: the core, the record's own source fields, the document-level fields records inherit, and
# fields DerridAI computes itself.
RESERVED_NAMES = (
    set(CORE_FIELDS) | set(SOURCE_BOUND_FIELDS) | set(MANIFEST_INHERITED_FIELDS)
    | {"language", "needs_review", "review_reason", "attribution_confidence", "semantic_classification_confidence", "extraction_quality",
       "inline_citation", "full_citation", "metadata", "field_evidence", "field_assessments", "queue_state_version"}
)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_FIELDS = 60
MAX_GROUPS = 6

ScalarFieldType = Literal["text", "number", "boolean", "choice", "list"]
FieldType = Literal["text", "number", "boolean", "choice", "list", "repeatable"]
FieldRole = Literal["scholarly", "structural", "document", "operational"]
ReviewVisibility = Literal["primary", "details", "hidden"]
# Where a field's value lives: on each record, or once for the whole corpus (every record of the build inherits it).
FieldScope = Literal["record", "corpus"]
# What an empty value blocks. "evidence": a record without it cannot be cited as RAG evidence; "publication": the
# build cannot be published.
DocumentRequirement = Literal["evidence", "publication"]

# Bibliographic facts about a source. DerridAI owns their names, meaning and how records inherit them (see
# corpus_segmentation._apply_manifest_metadata); a schema only configures their policy. The value is the stable identity.
DOCUMENT_FIELDS: dict[str, str] = {
    name: f"derridai.document.{name}"
    for name in (
        "title", "short_title", "original_title", "document_author", "translator", "publisher",
        "publication_place", "publication_year", "edition", "isbn", "language", "original_language",
        "document_is_translation", "document_type",
    )
}
_DEFAULT_REQUIRED_DOCUMENT_FIELDS = {"title", "document_author"}


def _identity_scope(value: str) -> str:
    scope = re.sub(r"[^a-z0-9_.-]+", "-", str(value).casefold()).strip("-.") or "value"
    return scope if scope[0].isalpha() else f"f-{scope}"


class RetrievalProfile(BaseModel):
    """Policy for evidence-bound reviewed precedents used during metadata enrichment.

    The profile intentionally contains only controls with implemented semantics.
    Older schema files may still contain the abandoned multi-workflow routing
    fields; those are migrated away here instead of remaining inert configuration.
    """

    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    max_items: int = Field(default=6, ge=0, le=50)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    include_corrections: bool = True
    include_confirmed_absence: bool = True
    # Reviewed corrections have their own quota so they cannot crowd out positive
    # precedents (and vice versa).
    max_corrections: int = Field(default=2, ge=0, le=20)
    # Optional analogy conditions, by stable field_id: prefer precedents whose
    # reviewed value for each listed field equals this record's reviewed value, and
    # drop ones that differ. Nothing is assumed about which fields exist; a condition
    # that cannot be compared (either side unreviewed) is skipped, not guessed.
    match_field_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_routing(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        if result.pop("use_for_metadata_enrichment", True) is False:
            result["enabled"] = False
        # These fields were serialized before they had production semantics.
        # Retrieval is field-specific evidence-bound metadata enrichment; response
        # and claim memory remain separate systems.
        for key in ("scope", "use_for_response_memory", "use_for_claim_memory"):
            result.pop(key, None)
        return result


class SchemaValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1, max_length=80)
    definition: str = Field(default="", max_length=600)


class SchemaMember(BaseModel):
    """One independently assertable value inside a repeatable SchemaField."""

    model_config = ConfigDict(extra="forbid")
    field_id: str = ""
    name: str
    label: str = Field(min_length=1, max_length=80)
    type: ScalarFieldType = "text"
    values: list[SchemaValue] = Field(default_factory=list, max_length=60)
    strict: bool = False
    instruction: str = Field(default="", max_length=1500)
    evidence: bool = False
    assess: bool = False
    review: bool = False
    pos_tags: list[str] = Field(default_factory=list, max_length=32)
    ner_tags: list[str] = Field(default_factory=list, max_length=32)
    retrieval_profile: RetrievalProfile | None = None
    equivalence_profile: EquivalenceProfile | None = None

    @model_validator(mode="before")
    @classmethod
    def _identity_default(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        name = str(result.get("name") or "").strip()
        if not str(result.get("field_id") or "").strip() and name:
            result["field_id"] = f"member-{uuid.uuid5(uuid.NAMESPACE_URL, 'derridai:member:' + name)}"
        return result

    @field_validator("field_id")
    @classmethod
    def _field_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{1,119}", value):
            raise ValueError("member field_id must be a stable identifier.")
        return value

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not NAME_RE.match(value):
            raise ValueError("A member name is lower-case letters, digits and underscores.")
        return value

    @model_validator(mode="after")
    def _valid_type(self) -> SchemaMember:
        if self.type == "choice" and not self.values:
            raise ValueError("A choice member needs at least one allowed value.")
        if self.type != "choice" and (self.values or self.strict):
            raise ValueError("Only a choice member has allowed values.")
        return self


class SchemaField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = ""
    name: str
    semantic_compatibility_id: str | None = Field(default=None, max_length=120)
    label: str = Field(min_length=1, max_length=80)
    type: FieldType = "text"
    group: str = "discourse"
    # Storage/display names are arbitrary. These properties describe how a field
    # participates in the product without hard-coding behavior to its name.
    role: FieldRole = "scholarly"
    review_visibility: ReviewVisibility = "primary"
    # "corpus": the value is shared by every record of the corpus, so it may be filled once, before segmentation, and
    # records inherit it. This is separate from ordinary bulk editing,
    # where a reviewer picks records and fields after the fact.
    scope: FieldScope = "record"
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
    # Optional linguistic hints used by deterministic suggestions and model prompts.
    pos_tags: list[str] = Field(default_factory=list, max_length=32)
    ner_tags: list[str] = Field(default_factory=list, max_length=32)
    retrieval_profile: RetrievalProfile | None = None
    # When differently written values are the same semantic value (review feedback, precedent
    # grouping, semantic indexing). Stored values and evidence are never rewritten.
    equivalence_profile: EquivalenceProfile | None = None
    # A repeatable field is one canonical Record field whose value is a bounded
    # list of stable instances. Members remain independently assertable.
    members: list[SchemaMember] = Field(default_factory=list, max_length=24)
    max_items: int | None = Field(default=None, ge=1, le=24)
    instance_label: str = Field(default="{label} {number}", min_length=1, max_length=120)

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
        if not str(result.get("semantic_compatibility_id") or "").strip() and name in SEMANTIC_COMPATIBILITY_IDS:
            result["semantic_compatibility_id"] = SEMANTIC_COMPATIBILITY_IDS[name]
        # Format 1: a work-wide field is a corpus-scoped one.
        if "applies_to_work" in result:
            legacy = result.pop("applies_to_work")
            result.setdefault("scope", "corpus" if legacy else "record")
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
        for label in [*self.pos_tags, *self.ner_tags]:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", label):
                raise ValueError("NLP tags must contain letters, digits, underscores or hyphens.")
        if self.type == "repeatable":
            if not self.members or self.max_items is None:
                raise ValueError("A repeatable field needs members and max_items.")
            member_names = [member.name for member in self.members]
            member_ids = [member.field_id for member in self.members]
            if len(member_names) != len(set(member_names)) or len(member_ids) != len(set(member_ids)):
                raise ValueError("Repeatable member names and identities must be unique.")
            if self.values or self.strict:
                raise ValueError("A repeatable field cannot have choice values.")
        elif self.members or self.max_items is not None:
            raise ValueError("Only a repeatable field has members and max_items.")
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

class DocumentFieldPolicy(BaseModel):
    """A schema's policy for one DerridAI-owned bibliographic field: what a missing value blocks.

    Document fields always hold one value for the whole corpus. Values are detected when a source loads; a person is
    asked only for a required field detection could not fill.
    """

    model_config = ConfigDict(extra="forbid")
    name: str
    required_for: list[DocumentRequirement] = Field(default_factory=list, max_length=2)

    @field_validator("name")
    @classmethod
    def _known(cls, value: str) -> str:
        if value not in DOCUMENT_FIELDS:
            raise ValueError(f"'{value}' is not a document field DerridAI knows.")
        return value

    @field_validator("required_for")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        return sorted(set(value))

    @property
    def field_id(self) -> str:
        return DOCUMENT_FIELDS[self.name]


def default_document_fields() -> list[DocumentFieldPolicy]:
    return [DocumentFieldPolicy(
            name=name,
            required_for=["evidence", "publication"] if name in _DEFAULT_REQUIRED_DOCUMENT_FIELDS else [],
        ) for name in DOCUMENT_FIELDS]


class MetadataSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format_version: int = FORMAT_VERSION
    schema_version: str = "1.0.0"
    id: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=600)
    groups: list[SchemaGroup] = Field(max_length=MAX_GROUPS)
    fields: list[SchemaField] = Field(default_factory=list, max_length=MAX_FIELDS)
    # Always one policy per DOCUMENT_FIELDS entry, in that order; missing ones (format 1) take the defaults.
    document_fields: list[DocumentFieldPolicy] = Field(default_factory=default_document_fields)

    @field_validator("document_fields", mode="after")
    @classmethod
    def _complete_document_fields(cls, value: list[DocumentFieldPolicy]) -> list[DocumentFieldPolicy]:
        given = {policy.name: policy for policy in value}
        if len(given) != len(value):
            raise ValueError("Each document field may have only one policy.")
        defaults = {policy.name: policy for policy in default_document_fields()}
        return [given.get(name) or defaults[name] for name in DOCUMENT_FIELDS]

    @model_validator(mode="before")
    @classmethod
    def _current_format(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = copy.deepcopy(value)
        groups = result.get("groups") if isinstance(result.get("groups"), list) else []
        fields = result.get("fields") if isinstance(result.get("fields"), list) else []
        # Migrate the short-lived format-3 repeatable-group draft losslessly.
        for group in groups:
            if not isinstance(group, dict):
                continue
            if not group.pop("repeatable", False):
                group.pop("group_id", None)
                group.pop("max_items", None)
                group.pop("instance_label", None)
                continue
            key = str(group.get("key") or "")
            old_members = [
                field for field in fields
                if isinstance(field, dict) and field.get("group") == key
            ]
            if not old_members:
                continue
            first = old_members[0]
            member_keys = {
                "field_id", "name", "label", "type", "values", "strict", "instruction",
                "evidence", "assess", "review", "pos_tags", "ner_tags",
                "retrieval_profile", "equivalence_profile",
            }
            fields = [field for field in fields if field not in old_members]
            fields.append({
                "field_id": group.pop("group_id", "")
                    or f"field-{uuid.uuid5(uuid.NAMESPACE_URL, 'derridai:field:' + key)}",
                "name": key,
                "label": group.get("label") or key,
                "type": "repeatable",
                "group": key,
                "role": first.get("role", "scholarly"),
                "review_visibility": first.get("review_visibility", "primary"),
                "scope": first.get("scope", "record"),
                "values": [],
                "strict": False,
                "instruction": "",
                "definitions_heading": "",
                "evidence": any(bool(item.get("evidence")) for item in old_members),
                "assess": any(bool(item.get("assess")) for item in old_members),
                "review": any(bool(item.get("review")) for item in old_members),
                "retrieval_profile": group.get("retrieval_profile"),
                "equivalence_profile": None,
                "pos_tags": [],
                "ner_tags": [],
                "members": [
                    {key: item[key] for key in member_keys if key in item}
                    for item in old_members
                ],
                "max_items": group.pop("max_items", None) or 8,
                "instance_label": group.pop("instance_label", None) or "{label} {number}",
            })
        result["groups"] = groups
        result["fields"] = fields
        result["format_version"] = FORMAT_VERSION
        return result

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
        known = set(self.field_identity_map().values()) | {field.field_id for field in self.fields}
        owners = [(f"field '{f.name}'", f.retrieval_profile, self.field_id(f.name)) for f in self.fields]
        owners += [(f"group '{g.key}'", g.retrieval_profile, None) for g in self.groups]
        for label, profile, own_id in owners:
            for match_id in (profile.match_field_ids if profile else []):
                if match_id not in known:
                    raise ValueError(f"The retrieval policy of {label} matches on an unknown field ({match_id}).")
                if match_id == own_id:
                    raise ValueError(f"The retrieval policy of {label} cannot match on the field itself.")
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

    def semantic_compatibility_id(self, name: str) -> str | None:
        if name in SEMANTIC_COMPATIBILITY_IDS:
            return SEMANTIC_COMPATIBILITY_IDS[name]
        field = next((item for item in self.fields if item.name == name), None)
        return field.semantic_compatibility_id if field else None

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

    def equivalence_profile_for(self, name: str) -> EquivalenceProfile:
        """Resolve a field's value-matching policy by its stable semantics.

        Explicit schema policy, then DerridAI's policy for the field's semantic
        compatibility id, then its type. ``identity_kind`` is always filled: a field
        that declares none is scoped to its own stable identity.
        """
        field = next((item for item in self.fields if item.name == name), None)
        if field is None and name not in CORE_FIELDS:
            raise KeyError(name)
        compat = self.semantic_compatibility_id(name) or ""
        scope = compat or (field.field_id if field else self.field_id(name))
        if field is not None and field.equivalence_profile is not None:
            profile = field.equivalence_profile
        elif compat in DEFAULT_EQUIVALENCE_PROFILES:
            profile = DEFAULT_EQUIVALENCE_PROFILES[compat]
        elif field is None or field.type in {"boolean", "number"}:
            profile = EquivalenceProfile(mode="exact")
        elif field.type == "choice":
            profile = EquivalenceProfile(mode="controlled" if field.strict else "text")
        else:
            profile = EquivalenceProfile(mode="text")
        return profile if profile.identity_kind else profile.model_copy(update={"identity_kind": _identity_scope(scope)})

    def family_fields(self) -> dict[str, set[str]]:
        """Group key to its field names; the core sits in its group. Same shape as METADATA_FAMILY_FIELDS."""
        out = {g.key: {f.name for f in self.fields_in(g.key)} for g in self.groups}
        out[CORE_GROUP] |= set(CORE_FIELDS)
        return out

    def evidence_fields(self) -> set[str]:
        return {
            f.name for f in self.fields if f.evidence or any(member.evidence for member in f.members)
        } | set(CORE_FIELDS)

    def attribution_fields(self) -> set[str]:
        return {
            f.name for f in self.fields if f.evidence or any(member.evidence for member in f.members)
        }

    def review_fields(self) -> list[str]:
        return list(CORE_FIELDS) + [
            f.name for f in self.fields
            if (f.review or any(member.review for member in f.members))
            and f.role != "operational" and f.review_visibility != "hidden"
        ]

    def record_review_fields(self) -> list[str]:
        """Fields intended for the ordinary human Record-review surface."""
        return list(CORE_FIELDS) + [
            f.name for f in self.fields
            if f.role != "operational" and f.review_visibility != "hidden"
        ]

    def by_name(self) -> dict[str, SchemaField]:
        return {f.name: f for f in self.fields}

    def shared_fields(self) -> list[SchemaField]:
        """Schema fields filled once for the corpus rather than per record."""
        return [f for f in self.fields if f.scope != "record"]

    def document_policy(self, name: str) -> DocumentFieldPolicy:
        return next(p for p in self.document_fields if p.name == name)

    def required_document_fields(self, requirement: str) -> list[str]:
        return [p.name for p in self.document_fields if requirement in p.required_for]

    def content_hash(self) -> str:
        body = self.model_dump(mode="json", exclude={"id"})
        for field in body.get("fields") or []:
            # Optional policies added after a schema was saved do not change its identity until set.
            if field.get("equivalence_profile") is None:
                field.pop("equivalence_profile", None)
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
    if payload["derridai_metadata_schema"] not in READABLE_FORMAT_VERSIONS:
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
    field_names: set[str] | list[str] | tuple[str, ...] | None = None,
) -> str:
    """The prompt for one group, in the same shape DerridAI has always used:

    opening text, the list of fields with their instructions, notes, definitions of any values that have them, closing
    remarks, the shared context block, then the evidence and assessment instructions.
    """
    group = schema.group(group_key)
    requested_fields = {str(name) for name in field_names} if field_names is not None else None
    fields = [
        field
        for field in schema.fields_in(group_key)
        if requested_fields is None
        or field.name in requested_fields
    ]
    region_types = allowed_region_types or REGION_TYPES
    roles = allowed_discourse_roles or DISCOURSE_ROLES
    lines: list[str] = []
    definitions: list[tuple[str, dict[str, str]]] = []
    boolean_fields = (["primary_text"] if group_key == CORE_GROUP else []) + [
        field.name for field in fields if field.type == "boolean"
    ]
    if boolean_fields:
        lines.append(
            "- Boolean fields (" + ", ".join(boolean_fields) + ") are three-state: true, false, or null. "
            "False is an explicit supported value, not absence. When the source supports false, return false "
            "with outcome=\"supported_value\". Use outcome=\"no_supported_value\" only with null when "
            "the field genuinely has no applicable value. For every Boolean field, its field_assessments "
            "entry MUST include assessed_value and that value MUST exactly repeat the corresponding metadata "
            "value as true, false, or null."
        )
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
        if field.pos_tags:
            lines.append(f"- {field.name} should prefer values supported by POS tags: {json.dumps(field.pos_tags)}.")
        if field.ner_tags:
            lines.append(
                f"- {field.name} should prefer named entities matching these entity-type "
                f"labels: {json.dumps(field.ner_tags)}."
            )
        described = {v.value: v.definition for v in field.values if v.definition}
        if described:
            definitions.append((field.definitions_heading or f"{field.name} values", described))
    lines += [f"- {note}" for note in group.notes]

    scoped_names = ([*CORE_FIELDS] if group_key == CORE_GROUP else []) + [field.name for field in fields]
    intro = group.intro.rstrip().replace("{fields}", _oxford(scoped_names))
    parts = [intro]
    for field in fields:
        if field.type == "repeatable":
            parts.append(
                f"Return metadata.{field.name} as a list of at most {field.max_items} objects. "
                "Each object MUST have one stable instance_id and the associated member fields "
                f"({_oxford([member.name for member in field.members])}). Keep the same "
                "instance_id when a person edits an instance. Numbered labels are display-only; "
                "never create numbered metadata keys."
            )
    if field_names is not None:
        parts.append(
            "THIS MODEL CALL IS FIELD-SCOPED. Return metadata and assessments only for: "
            + _oxford(scoped_names)
            + ". Other fields in this metadata family are already resolved by a higher-priority "
            "candidate or are outside this call's contract."
        )
    if lines:
        parts.append((group.fields_heading.rstrip() + "\n" if group.fields_heading else "") + "\n".join(lines))
    for heading, mapping in definitions:
        parts.append(f"Operational {heading} definitions:\n{json.dumps(mapping, ensure_ascii=False)}")
    if group.trailer.strip():
        parts.append(group.trailer.strip())
    assessed = (list(CORE_FIELDS) if group_key == CORE_GROUP else []) + [
        f.name for f in fields if f.assess or any(member.assess for member in f.members)
    ]
    footer = group.footer.replace("{fields}", _oxford(([*CORE_FIELDS] if group_key == CORE_GROUP else []) + [f.name for f in fields])).replace("{assessed_fields}", _oxford(assessed))
    return "\n\n".join(parts) + "\n\n" + base_context + "\n" + footer


# ---- the model's answer, generated from the schema ----------------------------------------------------------------

class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str = ""


AssessmentOutcome = Literal["supported_value", "no_supported_value", "uncertain"]
_ASSESSMENT_CONTROL_VALUES = frozenset({"supported_value", "no_supported_value"})


class FieldAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The key is required even when the model explicitly cannot estimate a
    # confidence.  ``null`` therefore means "reported unavailable", while an
    # omitted key is a structured-output failure that should be retried.
    confidence: float | None = Field(ge=0.0, le=1.0)
    needs_review: bool
    reason: str = Field(max_length=500)
    outcome: AssessmentOutcome


class BooleanFieldAssessment(FieldAssessment):
    """Assessment that independently echoes the Boolean value being supported.

    Metadata is the materialized proposal; this echo lets deterministic validation
    detect a model that returns (for example) metadata=false while explaining that
    the proposition is true. Natural-language reasons are never parsed as data.
    """

    assessed_value: bool | None


class MetadataResponseBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessed_fields_for_validation: ClassVar[tuple[str, ...]] = ()
    evidence_fields_for_validation: ClassVar[tuple[str, ...]] = ()
    boolean_fields_for_validation: ClassVar[frozenset[str]] = frozenset()
    forbidden_values_for_validation: ClassVar[dict[str, frozenset[str]]] = {}

    @model_validator(mode="after")
    def validate_metadata_assessment_consistency(self) -> MetadataResponseBase:
        metadata_obj = getattr(self, "metadata", None)
        metadata = metadata_obj.model_dump() if isinstance(metadata_obj, BaseModel) else dict(metadata_obj or {})
        assessments_obj = getattr(self, "field_assessments", None)
        assessments = assessments_obj.model_dump() if isinstance(assessments_obj, BaseModel) else dict(assessments_obj or {})

        def missing(value: Any) -> bool:
            return value is None or value == "" or value == []

        def leaked(candidate: str, forbidden: frozenset[str]) -> bool:
            normalized = candidate.strip().casefold()
            return normalized in forbidden or any(
                part.strip() in forbidden & _ASSESSMENT_CONTROL_VALUES
                for part in re.split(r"[,;|]", normalized)
            )

        # POS/NER labels and another field's closed-vocabulary tokens are prompt/schema
        # instructions, not scholarly metadata. Small models sometimes copy those tokens
        # verbatim into an open text/list field. Reject that structural leakage here before
        # reconciliation can turn it into a candidate value.
        if isinstance(metadata_obj, BaseModel):
            for field, forbidden in self.forbidden_values_for_validation.items():
                value = getattr(metadata_obj, field, None)
                rejected: list[str] = []

                if isinstance(value, str) and leaked(value, forbidden):
                    rejected = [value.strip()]
                    setattr(metadata_obj, field, None)
                elif isinstance(value, list):
                    kept: list[Any] = []
                    for item in value:
                        if isinstance(item, str) and leaked(item, forbidden):
                            rejected.append(item.strip())
                        else:
                            kept.append(item)
                    if rejected:
                        setattr(metadata_obj, field, kept)
                if rejected:
                    assessment_model = (
                        getattr(assessments_obj, field, None)
                        if isinstance(assessments_obj, BaseModel)
                        else None
                    )
                    if assessment_model is not None:
                        assessment_model.outcome = "uncertain"
                        assessment_model.needs_review = True
                        prior_reason = str(getattr(assessment_model, "reason", "") or "").strip()
                        labels = ", ".join(repr(item) for item in rejected[:4])
                        assessment_model.reason = (
                            "Rejected structured-vocabulary leakage from assessment states, POS/NER tags or another "
                            f"field's closed choices: {labels}."
                            + (f" {prior_reason}" if prior_reason else "")
                        )[:500]
            metadata = metadata_obj.model_dump()
            assessments = (
                assessments_obj.model_dump()
                if isinstance(assessments_obj, BaseModel)
                else dict(assessments_obj or {})
            )

        for field in self.assessed_fields_for_validation:
            assessment = assessments.get(field)
            if not isinstance(assessment, dict):
                continue
            value = metadata.get(field)
            outcome = str(assessment.get("outcome") or "")
            needs_review = bool(assessment.get("needs_review"))

            contradiction = ""
            if field in self.boolean_fields_for_validation:
                assessed_value = assessment.get("assessed_value")
                if assessed_value != value:
                    contradiction = (
                        f"boolean assessed_value={assessed_value!r} disagrees with "
                        f"metadata value={value!r}"
                    )
            if (
                not contradiction
                and field in self.boolean_fields_for_validation
                and value is False
                and outcome == "no_supported_value"
            ):
                # False is a substantive negative classification, not an empty value.
                # Treat a model's common "no supported value" wording as the supported
                # boolean answer only when its independent Boolean echo agrees.
                assessment_model = (
                    getattr(assessments_obj, field, None)
                    if isinstance(assessments_obj, BaseModel)
                    else None
                )
                if assessment_model is not None:
                    assessment_model.outcome = "supported_value"
                outcome = "supported_value"
            if not contradiction and outcome == "supported_value" and missing(value):
                contradiction = "outcome=supported_value but the metadata value is empty"
            elif not contradiction and outcome == "no_supported_value" and not missing(value):
                contradiction = "outcome=no_supported_value but a metadata value was returned"
            elif not contradiction and outcome == "uncertain" and not needs_review:
                contradiction = "outcome=uncertain but needs_review was false"

            if contradiction:
                # A contradictory assessment is a field-level epistemic failure,
                # not a reason to discard every otherwise-parseable value in the
                # metadata family. Preserve the proposed value, make the
                # contradiction explicit, and force human review. Downstream
                # reconciliation will materialize the field as unresolved rather
                # than treating the proposal as supported truth.
                assessment_model = (
                    getattr(assessments_obj, field, None)
                    if isinstance(assessments_obj, BaseModel)
                    else None
                )
                if assessment_model is not None:
                    assessment_model.outcome = "uncertain"
                    assessment_model.needs_review = True
                    prior_reason = str(getattr(assessment_model, "reason", "") or "").strip()
                    assessment_model.reason = (
                        f"Structured-output contradiction: {contradiction}."
                        + (f" {prior_reason}" if prior_reason else "")
                    )[:500]

            # Missing/invalid evidence is a review-state problem, not a
            # structured-output failure. Reconciliation below the schema layer
            # validates block membership/confidence and marks the individual field
            # evidence_failed so one omitted citation cannot discard an otherwise
            # usable metadata-family response.
        return self


def normalize_legacy_cardinality(field: SchemaField, value: Any) -> tuple[Any, bool]:
    """Normalize a historical value to the field\'s declared cardinality.

    The boolean reports an ambiguity that must remain reviewable instead of being
    guessed away. A one-item array is losslessly scalar; a multi-item array for a
    scalar field is not. Conversely, an old scalar for a list field can be wrapped
    as a one-item list without changing its value.
    """
    if field.type == "list":
        if value in (None, ""):
            return [], False
        return (value, False) if isinstance(value, list) else ([value], False)
    if not isinstance(value, list):
        return value, False
    if not value:
        return None, False
    if len(value) == 1:
        return value[0], False
    return value, True


def _annotation(field: SchemaField | SchemaMember) -> Any:
    if field.type == "boolean":
        return bool | None
    if field.type == "number":
        return float | None
    if field.type == "list":
        return Annotated[list[str], Field(max_length=24)]
    if field.type == "choice" and field.strict:
        return Literal[tuple(v.value for v in field.values)] | None
    return str | None


def _repeatable_annotation(field: SchemaField) -> Any:
    item_props: dict[str, Any] = {
        "instance_id": (
            Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]{1,119}$")],
            ...,
        )
    }
    for member in field.members:
        item_props[member.name] = (_annotation(member), ...)
    item = create_model(
        f"{field.name.title()}MetadataInstance",
        __config__=ConfigDict(extra="forbid"),
        **item_props,
    )

    def unique_instance_ids(values: list[BaseModel]) -> list[BaseModel]:
        ids = [value.model_dump(include={"instance_id"})["instance_id"] for value in values]
        if len(ids) != len(set(ids)):
            raise ValueError("Repeatable metadata instance_id values must be unique.")
        return values

    return Annotated[
        list[item],  # type: ignore[valid-type]
        Field(max_length=field.max_items),
        AfterValidator(unique_instance_ids),
    ]


def response_model_for(
    schema: MetadataSchema,
    group_key: str,
    *,
    region_types: list[str] | None = None,
    roles: list[str] | None = None,
    field_names: set[str] | list[str] | tuple[str, ...] | None = None,
) -> type[BaseModel]:
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
    requested_fields = {str(name) for name in field_names} if field_names is not None else None
    group_fields = [
        field
        for field in schema.fields_in(group_key)
        if requested_fields is None
        or field.name in requested_fields
    ]
    for field in group_fields:
        props[field.name] = (
            _repeatable_annotation(field) if field.type == "repeatable" else _annotation(field),
            ...,
        )
    metadata = create_model(f"{group_key.title()}Metadata", __config__=ConfigDict(extra="forbid"), **props)

    assessed_names = list(CORE_FIELDS) if group_key == CORE_GROUP else []
    assessed_names.extend(
        field.name for field in group_fields
        if field.assess or any(member.assess for member in field.members)
    )
    assessed_names = list(dict.fromkeys(assessed_names))
    boolean_fields = {"primary_text"} if group_key == CORE_GROUP else set()
    boolean_fields.update(field.name for field in group_fields if field.type == "boolean")

    fields: dict[str, Any] = {
        "metadata": (metadata, ...),
        "review_reason": (str, Field(default="", max_length=1000)),
    }
    if assessed_names:
        assessment_props: dict[str, Any] = {
            name: (
                BooleanFieldAssessment if name in boolean_fields else FieldAssessment,
                ...,
            )
            for name in assessed_names
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
    evidence_names.update(
        field.name for field in group_fields
        if field.evidence or any(member.evidence for member in field.members)
    )
    if evidence_names:
        fields["field_evidence"] = (dict[str, FieldEvidence], Field(default_factory=dict))

    response = create_model(
        f"{group_key.title()}MetadataResponse",
        __base__=MetadataResponseBase,
        **fields,
    )
    response.assessed_fields_for_validation = tuple(assessed_names)
    response.evidence_fields_for_validation = tuple(sorted(evidence_names))
    response.boolean_fields_for_validation = frozenset(boolean_fields)

    # Open text/list values must never be populated from the schema's own control
    # vocabulary. A strict choice is enforced by JSON Schema already; for open fields
    # reject exact copies of POS/NER labels and other fields' closed choices.
    machine_labels = {
        str(tag).strip().casefold()
        for schema_field in schema.fields
        for tag in [*schema_field.pos_tags, *schema_field.ner_tags]
        if str(tag).strip()
    }
    closed_values = {
        str(value).strip().casefold()
        for value in [*(region_types or REGION_TYPES), *(roles or DISCOURSE_ROLES)]
        if str(value).strip()
    }
    for schema_field in schema.fields:
        if schema_field.type == "choice" and schema_field.strict:
            closed_values.update(
                str(item.value).strip().casefold()
                for item in schema_field.values
                if str(item.value).strip()
            )
    forbidden: dict[str, frozenset[str]] = {}
    for schema_field in group_fields:
        if schema_field.type not in {"text", "list"}:
            continue
        own_values = {
            str(item.value).strip().casefold()
            for item in schema_field.values
            if str(item.value).strip()
        }
        forbidden[schema_field.name] = frozenset(
            machine_labels | ((closed_values | _ASSESSMENT_CONTROL_VALUES) - own_values)
        )
    response.forbidden_values_for_validation = forbidden
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
    "and outcome. Keep every assessment reason to one short sentence. Never put a proposed value only in the reason: outcome=\"supported_value\" "
    "requires the corresponding metadata value to be non-null/non-empty. Use outcome=\"no_supported_value\" when the source supports that no "
    "value applies, and outcome=\"uncertain\" when the field cannot be determined. Mark needs_review=true whenever "
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
    "short reason. Use null for an unsupported scalar quotation relation and [] for an unsupported quotation_chain.\n"
    "Return one field_assessments entry for every one of {assessed_fields}, even when its metadata value is null or empty. Each assessment must "
    "contain confidence (0..1 or null), needs_review, reason, and outcome. For is_direct_quote specifically, false is an explicit "
    "supported classification: return is_direct_quote=false with outcome=\"supported_value\" when the source supports that no direct "
    "quotation is present; reserve outcome=\"no_supported_value\" for a null value when the field is genuinely inapplicable. Keep each reason "
    "to one short sentence and never put a proposed value only in the reason. Otherwise use "
    "outcome=\"supported_value\", outcome=\"no_supported_value\", or outcome=\"uncertain\" according to the source evidence.\n"
)
_INDEXING_INTRO = (
    "Infer ONLY conservative semantic indexing metadata for one immutable DerridAI record.\n"
    "Return {fields} when materially present in this record. Do not infer discourse attribution, "
    "quotation ownership, bibliography, summaries, or source text. Prefer a short precise list to speculative coverage; emit brief noun phrases "
    "or proper names, not full sentences or explanatory clauses. Example: concepts=[\"cities of refuge\"] is acceptable; concepts=[\"The concept "
    "and practice of 'cities of refuge' as a form of cosmopolitics distinct from state sovereignty.\"] is not."
)
_INDEXING_FOOTER = (
    "Return one field_assessments entry for every one of {assessed_fields}, even when the corresponding metadata list is empty. Each assessment "
    "must contain confidence (0..1 or null), needs_review, reason, and outcome. Keep each reason to one short sentence. Use "
    "outcome=\"supported_value\" only for a supported non-empty list, outcome=\"no_supported_value\" when the record supports an empty list, "
    "and outcome=\"uncertain\" when the field cannot be "
    "determined.\n"
)


# Curated lexical candidate hints for every configurable field in the built-in
# scholarly schema. These are candidate-generation hints only: matching a POS or
# entity tag never establishes a metadata value, discourse role, or evidence
# binding. Empty tuples are intentional for fields whose value is a classification
# inferred from the passage rather than a surface form. The locked core fields
# (region_type, primary_text, discourse_role) are likewise classifications and do
# not participate in schema-configured lexical candidate generation.
_DEFAULT_SCHEMA_NLP_HINTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "region_author": (("PROPN",), ("PERSON", "ORG")),
    "speaker": (("PRON", "PROPN", "NOUN"), ("PERSON", "ORG", "NORP")),
    "position_holder": (("PRON", "PROPN", "NOUN"), ("PERSON", "ORG", "NORP")),
    "target": (
        ("PROPN", "NOUN"),
        ("PERSON", "ORG", "NORP", "GPE", "LOC", "EVENT", "LAW", "LANGUAGE", "WORK_OF_ART"),
    ),
    "stance": ((), ()),
    "proposition_status": ((), ()),
    "claim_scope": (("ADJ", "NOUN", "PROPN"), ()),
    "semantic_function": ((), ()),
    "is_direct_quote": ((), ()),
    "quoted_speaker": (("PRON", "PROPN", "NOUN"), ("PERSON", "ORG", "NORP")),
    "quoted_author": (("PROPN",), ("PERSON", "ORG")),
    "quoted_work": (("PROPN", "NOUN"), ("WORK_OF_ART", "LAW")),
    "quoted_position_holder": (("PRON", "PROPN", "NOUN"), ("PERSON", "ORG", "NORP")),
    "quoted_addressee": (("PRON", "PROPN", "NOUN"), ("PERSON", "ORG", "NORP")),
    "quoted_referent": (
        ("PRON", "PROPN", "NOUN"),
        ("PERSON", "ORG", "NORP", "GPE", "LOC", "EVENT", "LAW", "LANGUAGE", "WORK_OF_ART"),
    ),
    "quotation_chain": (("PROPN",), ("PERSON", "ORG", "WORK_OF_ART")),
    "topics": (
        ("ADJ", "NOUN", "PROPN"),
        ("EVENT", "GPE", "LOC", "NORP", "ORG", "LANGUAGE", "LAW"),
    ),
    "concepts": (("ADJ", "NOUN", "PROPN"), ()),
    "persons": (("PROPN",), ("PERSON",)),
    "works_referenced": (("PROPN", "NOUN"), ("WORK_OF_ART", "LAW")),
}


def _f(name: str, label: str, type_: FieldType, group: str, **kw: Any) -> SchemaField:
    pos_tags, ner_tags = _DEFAULT_SCHEMA_NLP_HINTS[name]
    return SchemaField(
        name=name, label=label, type=type_, group=group,
        semantic_compatibility_id=SEMANTIC_COMPATIBILITY_IDS.get(name),
        evidence=name in ATTRIBUTION_EVIDENCE_FIELDS, review=name in REVIEW_METADATA_FIELDS,
        pos_tags=list(pos_tags), ner_tags=list(ner_tags), **kw,
    )


def default_schema() -> MetadataSchema:
    """DerridAI's built-in scholarly fields with authoritative current value types."""
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
        *[_f(n, lab, "text", "quotation", assess=True) for n, lab in (
            ("quoted_speaker", "Quoted speaker"), ("quoted_author", "Quoted author"), ("quoted_work", "Quoted work"),
            ("quoted_position_holder", "Quoted position holder"), ("quoted_addressee", "Quoted addressee"),
            ("quoted_referent", "Quoted referent"))],
        _f("quotation_chain", "Quotation chain", "list", "quotation", assess=True),
        *[_f(n, lab, "list", "indexing", assess=True) for n, lab in (
            ("topics", "Topics"), ("concepts", "Concepts"), ("persons", "Persons"), ("works_referenced", "Works referenced"))],
    ]
    return MetadataSchema(
        id=DEFAULT_SCHEMA_ID, schema_version="2.0.0", name="DerridAI scholarly default",
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
        elif field.type == "repeatable":
            annotation = _repeatable_annotation(field)
        props[field.name] = (annotation | None if field.type != "list" else annotation, Field(default_factory=list) if field.type == "list" else None)
    return create_model("RecordEdit", __config__=ConfigDict(extra="forbid"), **props)

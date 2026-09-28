# Copyright 2026 Aaron John Schlosser, PhD.
"""Provider-neutral identity and candidate types for Corpus Capture.

The scholarly chain here is PERSON → ABSTRACT WORK → EDITION/TRANSLATION →
PROVIDER REPRESENTATION → SourceDocument. These types keep those levels apart:
a :class:`SourceCandidate` is one provider representation, never a work, and
nothing in this module merges two candidates.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

CAPTURE_CONTRACT_VERSION = "derridai-corpus-capture-v1"


class ContributionRole(StrEnum):
    """The selected person's role for one provider representation (closed vocabulary)."""

    AUTHOR = "author"
    COAUTHOR = "coauthor"
    TRANSLATOR = "translator"
    EDITOR = "editor"
    CONTRIBUTOR = "contributor"
    ABOUT_AUTHOR = "about_author"  # material about the person; never authorship
    UNKNOWN = "unknown"


class WorkRelationship(StrEnum):
    ORIGINAL_LANGUAGE_EDITION = "original_language_edition"
    TRANSLATION = "translation"
    EDITION = "edition"
    UNKNOWN = "unknown"


class CaptureErrorCode(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RATE_LIMITED = "rate_limited"
    AUTHOR_NOT_FOUND = "author_not_found"
    AMBIGUOUS_AUTHOR = "ambiguous_author"
    CATALOG_UNAVAILABLE = "catalog_unavailable"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    SOURCE_NOT_FOUND = "source_not_found"
    UNSUPPORTED_SOURCE = "unsupported_source"
    SOURCE_TOO_LARGE = "source_too_large"
    NETWORK_TIMEOUT = "network_timeout"
    IDENTITY_MISMATCH = "identity_mismatch"
    INVALID_OPTIONS = "invalid_options"
    ACQUISITION_FAILED = "acquisition_failed"
    REGISTRATION_FAILED = "registration_failed"
    CANCELLED = "cancelled"


# Transient failures may be retried with backoff; the rest are deterministic.
TRANSIENT_ERRORS = frozenset(
    {CaptureErrorCode.PROVIDER_UNAVAILABLE, CaptureErrorCode.RATE_LIMITED, CaptureErrorCode.NETWORK_TIMEOUT}
)


class CaptureError(Exception):
    """A classified, user-presentable failure. ``detail`` is diagnostic only."""

    def __init__(self, code: CaptureErrorCode, message: str, *, detail: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    @property
    def transient(self) -> bool:
        return self.code in TRANSIENT_ERRORS

    def to_dict(self) -> dict[str, str]:
        return {"code": str(self.code), "message": self.message}


# --- Language -----------------------------------------------------------------

_LANGUAGE_ALIASES = {
    # ISO 639-2/B and common catalogue spellings → BCP 47 primary subtags.
    "eng": "en", "fre": "fr", "fra": "fr", "ger": "de", "deu": "de", "lat": "la", "gre": "el",
    "ell": "el", "grc": "grc", "ita": "it", "spa": "es", "por": "pt", "rus": "ru", "dut": "nl",
    "nld": "nl", "english": "en", "french": "fr", "german": "de", "latin": "la",
}
_LANGUAGE_CODE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$")


def normalize_language(value: str | None) -> str | None:
    """A lower-case BCP 47 tag, or ``None`` when the value is not a recognisable code.

    Unknown remains unknown: this never guesses a language from a name or title.
    """
    text = str(value or "").strip().lower().replace("_", "-")
    if not text:
        return None
    text = _LANGUAGE_ALIASES.get(text, text)
    return text if _LANGUAGE_CODE.match(text) else None


def normalize_languages(values: Any) -> list[str]:
    raw = re.split(r"[;,\s]+", values) if isinstance(values, str) else list(values or [])
    out: list[str] = []
    for item in raw:
        code = normalize_language(str(item))
        if code and code not in out:
            out.append(code)
    return out


# --- Person names ---------------------------------------------------------------


def fold(text: str) -> str:
    """Case- and diacritic-insensitive comparison form (Nietzsche == NIETZSCHE, Böhme == Bohme)."""
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^\w]+", " ", stripped.casefold()).strip()


@dataclass(frozen=True)
class PersonName:
    """A name split into comparison keys; built from "Last, First" or "First Last" forms."""

    full: str  # folded "given ... surname"
    surname: str
    first_given: str

    @classmethod
    def parse(cls, name: str) -> PersonName:
        cleaned = re.sub(r"\([^)]*\)", " ", str(name or ""))  # drop "(Anthony Mario)" expansions
        if cleaned.count(",") >= 1:
            last, rest = cleaned.split(",", 1)
            given = fold(rest).split()
            surname = fold(last)
        else:
            parts = fold(cleaned).split()
            surname = parts[-1] if parts else ""
            given = parts[:-1]
        full = " ".join([*given, surname]).strip()
        return cls(full=full, surname=surname, first_given=given[0] if given else "")


# --- Identity -------------------------------------------------------------------


@dataclass
class AuthorCandidate:
    """One person offered to the user during author resolution. Never auto-selected."""

    wikidata_qid: str
    label: str
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    birth_year: int | None = None
    death_year: int | None = None
    wikisource_sitelinks: dict[str, str] = field(default_factory=dict)  # project language → author page title
    # Only authoritative work-level evidence belongs here. Spoken languages and
    # Wikisource project languages remain in ``languages`` and must not be used
    # as an original-language default.
    original_languages: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResolvedAuthor:
    """The person a capture is bound to, as chosen explicitly by the user."""

    identity_id: str
    canonical_name: str
    wikidata_qid: str | None = None
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    birth_year: int | None = None
    death_year: int | None = None
    languages: list[str] = field(default_factory=list)
    external_ids: dict[str, str] = field(default_factory=dict)
    wikisource_sitelinks: dict[str, str] = field(default_factory=dict)
    original_languages: list[str] = field(default_factory=list)

    def names(self) -> list[str]:
        return list(dict.fromkeys([self.canonical_name, *self.aliases]))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResolvedAuthor:
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class CaptureOptions:
    providers: list[str] = field(default_factory=lambda: ["gutenberg", "wikisource"])
    # Roles included by default: works by the person (sole or co-author) and their editions/translations.
    roles: list[str] = field(default_factory=lambda: [ContributionRole.AUTHOR, ContributionRole.COAUTHOR])
    include_translations: bool = True
    include_originals: bool = True
    languages: list[str] | None = None  # None = all available languages
    max_candidates_per_provider: int = 2000

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "roles": [str(role) for role in self.roles]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaptureOptions:
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def validate_for_author(self, author: ResolvedAuthor) -> None:
        """Require an explicit single language when originals are not known.

        ``ResolvedAuthor.languages`` contains discovery signals (spoken and
        project languages), not an authoritative language of the author's
        works.  Only an explicitly supplied language or exactly one
        authoritative original-language signal may satisfy this constraint.
        """
        if self.include_translations:
            return
        known = list(dict.fromkeys(author.original_languages))
        requested = list(dict.fromkeys(self.languages or []))
        if not requested and len(known) == 1:
            self.languages = known
            return
        if len(requested) != 1:
            raise CaptureError(
                CaptureErrorCode.INVALID_OPTIONS,
                "Choose exactly one original language when translations are excluded.",
            )


@dataclass
class SourceCandidate:
    """One provider representation discovered for the resolved person."""

    provider: str
    provider_item_id: str
    title: str
    source_uri: str
    contribution_role: str = ContributionRole.UNKNOWN
    provider_author_identity: str = ""
    document_author: str = ""
    contributors: list[dict[str, Any]] = field(default_factory=list)
    document_languages: list[str] = field(default_factory=list)
    original_language: str | None = None
    source_project_language: str | None = None
    translators: list[str] = field(default_factory=list)
    editors: list[str] = field(default_factory=list)
    publication_year: int | None = None
    publisher: str | None = None
    edition: str | None = None
    catalog_uri: str | None = None
    provider_page_id: int | None = None
    provider_revision_id: int | None = None
    wikidata_work_id: str | None = None
    wikidata_edition_id: str | None = None
    relationship_to_work: str = WorkRelationship.UNKNOWN
    rights_status: str | None = None
    license: str | None = None
    copyright_tag: str | None = None
    rights_source: str | None = None
    discovery_method: str = ""
    discovery_evidence: dict[str, Any] = field(default_factory=dict)
    identity_confidence: str = "exact"  # exact | probable | needs_review

    @property
    def provider_key(self) -> str:
        return f"{self.provider}:{self.provider_item_id}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["contribution_role"] = str(self.contribution_role)
        data["relationship_to_work"] = str(self.relationship_to_work)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceCandidate:
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})

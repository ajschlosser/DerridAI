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

"""Deterministic semantic identity and value equivalence for metadata values.

A reviewer who changes ``J.P. Dingus`` to ``J. P. Dingus`` has not corrected the model;
they have restated the same value.  This module decides, deterministically and without
embeddings or model calls, whether two metadata values are the *same semantic value*:

``exact``
    The raw values are identical.
``equivalent``
    The surface differs but the identity is the same (an established identity, a
    reviewed alias, or a field-aware normalization says so).
``different``
    The values are distinct semantic values.
``unknown``
    Equivalence can be neither established nor ruled out (for example ``J. Dingus`` and
    ``John Dingus``, or two inflected phrases when no lemmatizer is installed).  Unknown
    is never treated as a difference: it must not produce a correction precedent.

Surface values are never rewritten.  Keys and identities computed here are derived,
versioned and rebuildable; the stored model value, reviewer value and evidence stay
exactly as they were.  Semantic relatedness is not equivalence: ``critique of
metaphysics`` and ``deconstruction of metaphysics`` stay different.

This module owns identity only.  It does not import review, graph, Chroma or route code;
callers pass a :class:`~app.semantic_identity_registry.SemanticIdentityRegistry` when they
have established identities to consult.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from .semantic_identity_registry import SemanticIdentityRegistry

# Bump when a normalization or precedence rule changes meaning. Review decisions and derived
# projections record the version they were computed with, so a later version never rewrites
# what an earlier decision meant.
SEMANTIC_IDENTITY_VERSION = 1

IdentityRelation = Literal["exact", "equivalent", "different", "unknown"]
EquivalenceMode = Literal["exact", "text", "entity_name", "lexical_phrase", "controlled"]
CollectionSemantics = Literal["set", "ordered"]
# Relations under which a reviewer kept the model's value.
SAME_RELATIONS: frozenset[str] = frozenset({"exact", "equivalent"})

# A token is (surface text, lemma, coarse part of speech).
LemmaToken = tuple[str, str, str]
Lemmatizer = Callable[[str, str], "list[LemmaToken] | None"]


class EquivalenceProfile(BaseModel):
    """How a field decides that two differently written values are the same value.

    ``identity_kind`` scopes identities (``person``, ``concept``, ...) so that a person
    called Derrida never collapses with a concept labelled Derrida.  Fields that declare
    the same kind share identities; a field that declares none is scoped to itself.
    """

    model_config = ConfigDict(extra="forbid")
    mode: EquivalenceMode = "text"
    collection_semantics: CollectionSemantics = "set"
    identity_kind: str | None = Field(default=None, max_length=120, pattern=r"^[a-z][a-z0-9_.-]{0,119}$")


class SemanticIdentityRef(BaseModel):
    identity_id: str
    kind: str
    canonical_label: str
    aliases: list[str] = Field(default_factory=list)
    source: str
    source_ids: list[str] = Field(default_factory=list)
    version: int = SEMANTIC_IDENTITY_VERSION


class ValueEquivalenceResult(BaseModel):
    relation: IdentityRelation
    left_identity_id: str | None = None
    right_identity_id: str | None = None
    left_key: str | None = None
    right_key: str | None = None
    profile: str
    reason_codes: list[str] = Field(default_factory=list)
    version: int = SEMANTIC_IDENTITY_VERSION

    @property
    def same(self) -> bool:
        return self.relation in SAME_RELATIONS

    def audit(self) -> dict[str, Any]:
        """Compact provenance for review decisions and ledger rows."""
        out: dict[str, Any] = {
            "equivalence_relation": self.relation,
            "equivalence_profile": self.profile,
            "equivalence_version": self.version,
            "equivalence_reasons": list(self.reason_codes),
        }
        identity = self.right_identity_id or self.left_identity_id
        if self.relation == "equivalent" and identity:
            out["semantic_identity_id"] = identity
        return out


# --- Surface normalization -------------------------------------------------------------------

_QUOTES = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "´": "'", "`": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"', "«": '"', "»": '"',
})
# Hyphen-like characters that NFKC leaves distinct. Dashes used as separators are unified too;
# minus signs are left alone because they can carry a number's meaning.
_DASHES = str.maketrans({c: "-" for c in "‐‑‒–—―﹘﹣－"})


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or (isinstance(value, str) and not value.strip())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _surface(text: str) -> str:
    """NFKC, unified quotes and dashes, collapsed whitespace; case preserved."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES).translate(_DASHES)
    return " ".join(text.split())


def text_key(text: str) -> str:
    """The ``text`` profile: surface normalization plus casefolding. No stemming."""
    return _surface(text).casefold()


_NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md", "esq"}
_INITIALS_RUN = re.compile(r"^[A-Z]{2,3}$")


def _name_tokens(text: str) -> list[str]:
    surface = _surface(text)
    head, sep, tail = surface.partition(",")
    # "Dingus, J. P." is "J. P. Dingus"; "Dingus, Jr." is not an inversion.
    if sep and "," not in tail and head.strip() and tail.strip() and tail.strip(" .").casefold() not in _NAME_SUFFIXES:
        surface = f"{tail.strip()} {head.strip()}"
    raw = [part for part in re.split(r"[\s.]+", surface) if part]
    tokens: list[str] = []
    for index, part in enumerate(raw):
        part = part.strip(",;:")
        if not part:
            continue
        # "JP Dingus": an all-capital run before the surname is a run of initials.
        if index < len(raw) - 1 and _INITIALS_RUN.match(part):
            tokens.extend(part.casefold())
        else:
            tokens.append(part.casefold())
    return tokens


def entity_name_key(text: str) -> str:
    """The ``entity_name`` profile: initials, their punctuation and inverted order normalized."""
    return " ".join(_name_tokens(text))


def _strip_marks(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _names_may_match(left: str, right: str) -> str | None:
    """A reason code when two differently keyed names could still name the same person."""
    a, b = _name_tokens(left), _name_tokens(right)
    if not a or not b:
        return None
    if _strip_marks(" ".join(a)) == _strip_marks(" ".join(b)):
        return "diacritic_variant"
    if a[-1] == b[-1]:
        return "shared_surname"  # "J. Dingus" / "John Dingus", "Dingus" / "J. P. Dingus"
    if (len(a) == 1 and a[0] in b) or (len(b) == 1 and b[0] in a):
        return "partial_name"
    return None


# --- Lexical phrases -------------------------------------------------------------------------

# Inflection is only normalized for nouns and verbs: comparatives and adverbs can carry the
# proposition ("better" is not "good"), so modifiers keep their surface form.
_LEMMATIZED_POS = {"NOUN", "VERB", "AUX"}
_WORD = re.compile(r"\w+(?:['’]\w+)*", re.UNICODE)


def lexical_key(tokens: Sequence[LemmaToken]) -> str:
    """The ``lexical_phrase`` identity text of already-tagged tokens."""
    return _lexical_key(tokens)


def _lexical_key(tokens: Sequence[LemmaToken]) -> str:
    out: list[str] = []
    for text, lemma, pos in tokens:
        if not str(text).strip() or pos in {"PUNCT", "SPACE"}:
            continue
        lemma_l = str(lemma or "").casefold()
        if lemma_l == "not":
            out.append("not")  # "n't" and "not" are the same negation, and both are kept
        elif pos in _LEMMATIZED_POS and lemma_l:
            out.append(lemma_l)
        else:
            out.append(str(text).casefold())
    return " ".join(out)


def _could_be_inflections(left: str, right: str) -> bool:
    """Whether two phrases differ only where inflection could explain it.

    Used only when no lemmatizer is available, and only to choose between ``unknown`` and
    ``different``: it can never establish equivalence.
    """
    a, b = _WORD.findall(text_key(left)), _WORD.findall(text_key(right))
    if not a or len(a) != len(b):
        return False
    for x, y in zip(a, b, strict=True):
        if x == y:
            continue
        common = 0
        for cx, cy in zip(x, y, strict=False):
            if cx != cy:
                break
            common += 1
        if common < max(3, min(len(x), len(y)) - 2):
            return False
    return True


_lemmatizer_override: Lemmatizer | None = None


def default_lemmatizer(text: str, language: str) -> list[LemmaToken] | None:
    """Tokens from the installed spaCy pipeline for ``language``, or None when unavailable."""
    if _lemmatizer_override is not None:
        return _lemmatizer_override(text, language)
    from .nlp_annotations import lemma_tokens

    return lemma_tokens(text, language)


def set_default_lemmatizer(lemmatizer: Lemmatizer | None) -> None:
    """Replace the process default (tests, or a provider installed at startup)."""
    global _lemmatizer_override
    _lemmatizer_override = lemmatizer


# --- Keys and comparison ---------------------------------------------------------------------

def _kind(profile: EquivalenceProfile, kind: str | None) -> str:
    return str(kind or profile.identity_kind or "value")


def _scalar_key(value: Any, mode: EquivalenceMode, *, language: str, lemmatizer: Lemmatizer | None) -> str | None:
    """The deterministic key of one scalar under ``mode``; None when it cannot be computed safely."""
    if not isinstance(value, str) or mode == "exact":
        return canonical_json(value)
    if mode == "entity_name":
        return entity_name_key(value)
    if mode == "lexical_phrase":
        tokens = (lemmatizer or default_lemmatizer)(_surface(value), language) if language else None
        return _lexical_key(tokens) if tokens else None
    return text_key(value)  # text, controlled


def canonical_value_key(
    value: Any,
    *,
    profile: EquivalenceProfile,
    kind: str | None = None,
    language: str = "",
    registry: SemanticIdentityRegistry | None = None,
    lemmatizer: Lemmatizer | None = None,
) -> str | None:
    """A derived key that equivalent values share; None when no safe key exists.

    An established identity wins over normalization. Lists use their collection semantics.
    """
    scope = _kind(profile, kind)
    if _is_empty(value):
        return None
    if isinstance(value, list):
        keys = [canonical_value_key(item, profile=profile, kind=scope, language=language, registry=registry, lemmatizer=lemmatizer) for item in value]
        if any(key is None for key in keys):
            return None
        members = [str(key) for key in keys]
        return canonical_json(members if profile.collection_semantics == "ordered" else sorted(set(members)))
    identity = resolve_identity(value, profile=profile, kind=scope, registry=registry)
    if identity is not None:
        return identity.identity_id
    if registry is not None and isinstance(value, str) and registry.ambiguous(value=value, kind=scope, mode=profile.mode):
        # A surface that could name several reviewed identities keys only to itself, so
        # nothing downstream merges it with any of them.
        return f"{scope}:ambiguous:{text_key(value)}"
    key = _scalar_key(value, profile.mode, language=language, lemmatizer=lemmatizer)
    return None if key is None else f"{scope}:{profile.mode}:{key}"


def resolve_identity(
    value: Any,
    *,
    profile: EquivalenceProfile,
    kind: str | None = None,
    language: str = "",
    registry: SemanticIdentityRegistry | None = None,
) -> SemanticIdentityRef | None:
    """The one established or reviewed identity ``value`` names, if the registry knows it."""
    if registry is None or not isinstance(value, str) or _is_empty(value):
        return None
    return registry.resolve(value=value, kind=_kind(profile, kind), mode=profile.mode, language=language, established_only=True)


def _result(relation: IdentityRelation, profile: EquivalenceProfile, reasons: list[str], **ids: Any) -> ValueEquivalenceResult:
    return ValueEquivalenceResult(relation=relation, profile=profile.mode, reason_codes=reasons, **ids)


def _compare_scalars(
    left: Any,
    right: Any,
    *,
    profile: EquivalenceProfile,
    kind: str,
    language: str,
    registry: SemanticIdentityRegistry | None,
    lemmatizer: Lemmatizer | None,
) -> ValueEquivalenceResult:
    if left == right and type(left) is type(right):
        return _result("exact", profile, [])
    blocked = False
    if registry is not None and isinstance(left, str) and isinstance(right, str):
        # 1. Established identities (explicit reviewed aliases, reviewed values) outrank normalization.
        from .semantic_identity_registry import REVIEWED_ALIAS

        left_ref = registry.resolve(value=left, kind=kind, mode=profile.mode, language=language, established_only=True)
        right_ref = registry.resolve(value=right, kind=kind, mode=profile.mode, language=language, established_only=True)
        ids = {
            "left_identity_id": left_ref.identity_id if left_ref else None,
            "right_identity_id": right_ref.identity_id if right_ref else None,
        }
        if left_ref and right_ref and left_ref.identity_id == right_ref.identity_id:
            return _result("equivalent", profile, ["shared_semantic_identity"], **ids)
        if left_ref and right_ref and left_ref.source == right_ref.source == REVIEWED_ALIAS:
            return _result("different", profile, ["distinct_semantic_identities"], **ids)
        # Two distinct reviewed identities, or a surface that could name several, must not be
        # merged by normalization afterwards.
        blocked = bool(left_ref and right_ref) or any(
            registry.ambiguous(value=value, kind=kind, mode=profile.mode) for value in (left, right)
        )
    mode = profile.mode
    if not isinstance(left, str) or not isinstance(right, str):
        mode = "exact"
    left_key = _scalar_key(left, mode, language=language, lemmatizer=lemmatizer)
    right_key = _scalar_key(right, mode, language=language, lemmatizer=lemmatizer)
    keys = {"left_key": left_key, "right_key": right_key}
    relation: IdentityRelation
    reasons: list[str]
    if left_key is not None and right_key is not None:
        if left_key == right_key and blocked:
            return _result("unknown", profile, ["ambiguous_semantic_identity"], **keys)
        if left_key == right_key:
            return _result("equivalent", profile, [f"{mode}_normalized"], **keys)
        relation, reasons = "different", [f"{mode}_distinct"]
        if mode == "entity_name":
            maybe = _names_may_match(left, right)
            if maybe:
                relation, reasons = "unknown", [maybe]
    elif text_key(left) == text_key(right) and blocked:
        return _result("unknown", profile, ["ambiguous_semantic_identity"], **keys)
    elif text_key(left) == text_key(right):
        # Surface normalization is safe for every textual profile, with or without a lemmatizer.
        return _result("equivalent", profile, ["text_normalized"], **keys)
    elif _could_be_inflections(left, right):
        relation, reasons = "unknown", ["lemmatizer_unavailable"]
    else:
        relation, reasons = "different", ["lexical_distinct"]
    if relation == "unknown" and registry is not None:
        # 2. Document Intelligence clusters may resolve an ambiguity, never override a difference.
        soft_left = registry.resolve(value=left, kind=kind, mode=profile.mode, language=language)
        soft_right = registry.resolve(value=right, kind=kind, mode=profile.mode, language=language)
        if soft_left and soft_right and soft_left.identity_id == soft_right.identity_id:
            return _result(
                "equivalent", profile, [*reasons, "document_intelligence_alias"],
                left_identity_id=soft_left.identity_id, right_identity_id=soft_right.identity_id, **keys,
            )
    return _result(relation, profile, reasons, **keys)


def compare_values(
    left: Any,
    right: Any,
    *,
    profile: EquivalenceProfile,
    kind: str | None = None,
    language: str = "",
    registry: SemanticIdentityRegistry | None = None,
    lemmatizer: Lemmatizer | None = None,
) -> ValueEquivalenceResult:
    """Decide whether ``left`` and ``right`` are the same semantic value under ``profile``."""
    scope = _kind(profile, kind)
    if left == right and type(left) is type(right):
        return _result("exact", profile, [])
    if _is_empty(left) and _is_empty(right):
        return _result("equivalent", profile, ["both_empty"])
    if _is_empty(left) or _is_empty(right):
        return _result("different", profile, ["one_empty"])
    if isinstance(left, list) or isinstance(right, list):
        return _compare_lists(
            left if isinstance(left, list) else [left],
            right if isinstance(right, list) else [right],
            profile=profile, kind=scope, language=language, registry=registry, lemmatizer=lemmatizer,
            wrapped=not (isinstance(left, list) and isinstance(right, list)),
        )
    return _compare_scalars(left, right, profile=profile, kind=scope, language=language, registry=registry, lemmatizer=lemmatizer)


def _compare_lists(
    left: list[Any],
    right: list[Any],
    *,
    profile: EquivalenceProfile,
    kind: str,
    language: str,
    registry: SemanticIdentityRegistry | None,
    lemmatizer: Lemmatizer | None,
    wrapped: bool,
) -> ValueEquivalenceResult:
    """One-to-one equivalence of every member; partial overlap is not equivalence."""
    extra = ["cardinality_normalized"] if wrapped else []
    if len(left) != len(right):
        return _result("different", profile, [*extra, "member_count_differs"])

    def compare(a: Any, b: Any) -> ValueEquivalenceResult:
        return compare_values(a, b, profile=profile, kind=kind, language=language, registry=registry, lemmatizer=lemmatizer)

    if profile.collection_semantics == "ordered":
        results = [compare(a, b) for a, b in zip(left, right, strict=True)]
    else:
        results = []
        remaining = list(range(len(right)))
        pending: list[Any] = []
        for item in left:  # pair every member that has a same-valued partner first
            match = next(((j, r) for j in remaining if (r := compare(item, right[j])).same), None)
            if match is None:
                pending.append(item)
            else:
                remaining.remove(match[0])
                results.append(match[1])
        for item in pending:  # then any member that might still be the same, without guessing a pairing
            match = next(((j, r) for j in remaining if (r := compare(item, right[j])).relation == "unknown"), None)
            if match is None:
                return _result("different", profile, [*extra, "member_differs"])
            remaining.remove(match[0])
            results.append(match[1])
    relations = {r.relation for r in results}
    reasons = sorted({code for r in results for code in r.reason_codes})
    if "different" in relations:
        return _result("different", profile, [*extra, "member_differs"])
    if "unknown" in relations:
        return _result("unknown", profile, [*extra, *reasons])
    if relations <= {"exact"} and not wrapped and left != right:
        return _result("equivalent", profile, [*extra, "member_order"])
    if relations <= {"exact"} and not wrapped:
        return _result("exact", profile, [])
    return _result("equivalent", profile, [*extra, *reasons])

# Copyright 2026 Aaron John Schlosser, PhD.
"""Isolated BookNLP adapter for DerridAI document intelligence.

The worker never downloads model weights.  BookNLP is constructed in custom-model
mode only after all configured artifacts exist.  Its native files are normalized
into a small provider-neutral JSON response; DerridAI remains responsible for
Record/source identity, evidence, review authority, and semantic interpretation.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import tempfile
import threading
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="DerridAI BookNLP worker", docs_url=None, redoc_url=None)
_lock = threading.Lock()
_models: dict[str, Any] = {}


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4_000_000)
    language: str = "en"
    document_id: str = Field(default="document", max_length=200)
    profile: Literal["general", "fiction", "scholarly"] = "scholarly"
    include_events: bool = False


def _paths(include_events: bool = False) -> dict[str, str]:
    # BookNLP's event head is part of the entity tagger model; it does not use a
    # separate event-model artifact. Keep one artifact contract for both modes.
    _ = include_events
    return {
        "entity_model_path": os.environ.get("BOOKNLP_ENTITY_MODEL", ""),
        "coref_model_path": os.environ.get("BOOKNLP_COREF_MODEL", ""),
        "quote_attribution_model_path": os.environ.get("BOOKNLP_QUOTE_MODEL", ""),
    }


def _missing_models(include_events: bool = False) -> list[str]:
    return [
        name
        for name, value in _paths(include_events).items()
        if not value or not Path(value).is_file()
    ]


def _expected_digest(role: str) -> str:
    env_by_role = {
        "entity_model_path": "BOOKNLP_ENTITY_SHA256",
        "coref_model_path": "BOOKNLP_COREF_SHA256",
        "quote_attribution_model_path": "BOOKNLP_QUOTE_SHA256",
    }
    return str(os.environ.get(env_by_role.get(role, ""), "") or "").strip().lower()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _artifact_manifest() -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for role, value in _paths().items():
        path = Path(value)
        if not value or not path.is_file():
            continue
        actual = _file_sha256(path)
        expected = _expected_digest(role)
        artifacts.append(
            {
                "role": role,
                "name": path.name,
                "sha256": actual,
                "expected_sha256": expected or None,
                "verified": bool(expected and actual == expected),
            }
        )
    return artifacts


def _digest_mismatches(
    artifacts: list[dict[str, Any]] | None = None,
) -> list[str]:
    mismatches: list[str] = []
    for artifact in artifacts if artifacts is not None else _artifact_manifest():
        expected = str(artifact.get("expected_sha256") or "")
        if expected and not artifact.get("verified"):
            mismatches.append(str(artifact.get("role") or "model"))
    return mismatches


def _pipeline(include_events: bool) -> Any:
    key = "entity,quote,coref,event" if include_events else "entity,quote,coref"
    if key in _models:
        return _models[key]
    missing = _missing_models(include_events)
    if missing:
        raise RuntimeError("Missing approved BookNLP model artifact(s): " + ", ".join(missing))
    mismatches = _digest_mismatches()
    if mismatches:
        raise RuntimeError(
            "BookNLP model digest verification failed for: " + ", ".join(mismatches)
        )
    with _lock:
        if key in _models:
            return _models[key]
        from booknlp.booknlp import BookNLP

        params: dict[str, Any] = {
            "pipeline": key,
            "model": "custom",
            "spacy_model": os.environ.get("BOOKNLP_SPACY_MODEL", "en_core_web_sm"),
            "pronominalCorefOnly": True,
            **_paths(include_events),
        }
        _models[key] = BookNLP("en", params)
        return _models[key]


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _int(row: dict[str, str], *keys: str, default: int = -1) -> int:
    for key in keys:
        try:
            return int(row.get(key, ""))
        except (TypeError, ValueError):
            continue
    return default


def _utf8_map(text: str) -> tuple[list[int], dict[int, int]]:
    """Compatibility map for BookNLP variants that emit true byte offsets.

    BookNLP 1.0.8 names its columns byte_onset/byte_offset but populates them
    from spaCy token.idx, which is a Python character offset. We therefore use
    raw character offsets first and only fall back to UTF-8 conversion when an
    offset lies beyond the character length.
    """
    boundaries = [0]
    lookup = {0: 0}
    total = 0
    for index, char in enumerate(text, start=1):
        total += len(char.encode("utf-8"))
        boundaries.append(total)
        lookup[total] = index
    return boundaries, lookup


def _utf8_to_char(offset: int, boundaries: list[int], lookup: dict[int, int]) -> int:
    if offset in lookup:
        return lookup[offset]
    return max(0, bisect_right(boundaries, max(0, offset)) - 1)


def _token_span(
    token_rows: list[dict[str, str]],
    start_token: int,
    end_token: int,
    text: str,
    boundaries: list[int],
    lookup: dict[int, int],
    expected_text: str = "",
) -> tuple[int, int]:
    selected = [
        row
        for row in token_rows
        if start_token <= _int(row, "token_ID_within_document", "tokenId", "token_ID") <= end_token
    ]
    if not selected and end_token > start_token:
        selected = [
            row
            for row in token_rows
            if start_token
            <= _int(row, "token_ID_within_document", "tokenId", "token_ID")
            < end_token
        ]
    if not selected:
        return -1, -1
    raw_start = min(_int(row, "byte_onset", "byte_start", default=0) for row in selected)
    raw_end = max(_int(row, "byte_offset", "byte_end", default=raw_start) for row in selected)
    if 0 <= raw_start <= raw_end <= len(text):
        # BookNLP 1.0.8 writes spaCy character offsets despite the historical
        # "byte_*" column names.
        start, end = raw_start, raw_end
    else:
        start = _utf8_to_char(raw_start, boundaries, lookup)
        end = _utf8_to_char(raw_end, boundaries, lookup)
    expected = expected_text.strip()
    if expected:
        broad_start = max(0, start - 2)
        broad_end = min(len(text), end + 2)
        local = text[broad_start:broad_end].find(expected)
        if local >= 0:
            start = broad_start + local
            end = start + len(expected)
    return start, max(start, end)


def _book_character_data(
    path: Path,
    token_rows: list[dict[str, str]],
    text: str,
    boundaries: list[int],
    lookup: dict[int, int],
) -> list[dict[str, Any]]:
    """Normalize BookNLP's .book character summaries without gender inference."""
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    characters = payload.get("characters") if isinstance(payload, dict) else None
    if not isinstance(characters, list):
        return []

    token_by_id = {
        _int(row, "token_ID_within_document", "tokenId", "token_ID"): row
        for row in token_rows
    }

    def syntax_items(raw: Any) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            token_id = _int(item, "i", "token_id")
            row = token_by_id.get(token_id)
            if row is None:
                output.append({"text": str(item.get("w") or ""), "token_id": token_id})
                continue
            start, end = _token_span(
                token_rows,
                token_id,
                token_id,
                text,
                boundaries,
                lookup,
                str(item.get("w") or ""),
            )
            output.append(
                {
                    "text": str(item.get("w") or row.get("word") or ""),
                    "lemma": str(row.get("lemma") or ""),
                    "token_id": token_id,
                    "start_char": start,
                    "end_char": end,
                }
            )
        return output

    normalized: list[dict[str, Any]] = []
    for character in characters:
        if not isinstance(character, dict):
            continue
        cid = str(character.get("id") or character.get("char_id") or character.get("coref") or "")
        if not cid:
            continue
        mentions = character.get("mentions")
        mentions = mentions if isinstance(mentions, dict) else {}
        aliases: list[str] = []
        mention_groups: dict[str, list[dict[str, Any]]] = {}
        for key in ("proper", "common", "pronoun"):
            values: list[dict[str, Any]] = []
            for item in mentions.get(key) if isinstance(mentions.get(key), list) else []:
                if isinstance(item, dict):
                    value = str(item.get("n") or item.get("name") or "").strip()
                    count = int(item.get("c") or item.get("count") or 0)
                else:
                    value = str(item or "").strip()
                    count = 0
                if not value:
                    continue
                aliases.append(value)
                values.append({"text": value, "count": count})
            mention_groups[key] = values
        normalized.append(
            {
                "cluster_id": cid,
                "aliases": list(dict.fromkeys(aliases)),
                "mention_count": int(character.get("count") or 0),
                "mentions": mention_groups,
                "actions_as_agent": syntax_items(character.get("agent")),
                "actions_as_patient": syntax_items(character.get("patient")),
                "possessions": syntax_items(character.get("poss")),
                "modifiers": syntax_items(character.get("mod")),
            }
        )
    return normalized


@app.get("/health")
def health() -> dict[str, Any]:
    missing = _missing_models(False)
    artifacts = _artifact_manifest() if not missing else []
    mismatches = _digest_mismatches(artifacts)
    return {
        "ready": not missing and not mismatches,
        "provider": "booknlp",
        "version": importlib.metadata.version("booknlp"),
        "missing_model_artifacts": missing,
        "digest_mismatches": mismatches,
        "model_artifacts": artifacts,
        "runtime_downloads": False,
    }


@app.post("/analyze")
def analyze(body: AnalyzeRequest) -> dict[str, Any]:
    if body.language.lower().split("-", 1)[0] != "en":
        raise HTTPException(status_code=422, detail="This BookNLP worker supports English only.")
    try:
        pipeline = _pipeline(body.include_events)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    with tempfile.TemporaryDirectory(prefix="derridai-booknlp-") as tmp:
        root = Path(tmp)
        source = root / "source.txt"
        out = root / "output"
        source.write_text(body.text, encoding="utf-8")
        out.mkdir()
        book_id = "document"
        try:
            pipeline.process(str(source), str(out), book_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"BookNLP analysis failed: {exc}") from exc

        tokens = _rows(out / f"{book_id}.tokens")
        entities_native = _rows(out / f"{book_id}.entities")
        quotes_native = _rows(out / f"{book_id}.quotes")
        boundaries, byte_lookup = _utf8_map(body.text)
        characters = _book_character_data(
            out / f"{book_id}.book",
            tokens,
            body.text,
            boundaries,
            byte_lookup,
        )
        aliases = {
            str(character.get("cluster_id") or ""): [
                str(value)
                for value in (character.get("aliases") or [])
                if str(value).strip()
            ]
            for character in characters
            if character.get("cluster_id")
        }

        entities: list[dict[str, Any]] = []
        for row in entities_native:
            cluster_id = str(row.get("COREF") or row.get("coref") or row.get("char_id") or "")
            expected = str(row.get("text") or "")
            start, end = _token_span(
                tokens,
                _int(row, "start_token", "startToken"),
                _int(row, "end_token", "endToken"),
                body.text,
                boundaries,
                byte_lookup,
                expected,
            )
            if start < 0 or end <= start:
                continue
            entities.append(
                {
                    "cluster_id": cluster_id,
                    "start_char": start,
                    "end_char": end,
                    "text": body.text[start:end] or expected,
                    "mention_type": str(row.get("prop") or ""),
                    "entity_type": str(row.get("cat") or ""),
                }
            )

        quotations: list[dict[str, Any]] = []
        for row in quotes_native:
            expected = str(row.get("quote") or "")
            start, end = _token_span(
                tokens,
                _int(row, "quote_start"),
                _int(row, "quote_end"),
                body.text,
                boundaries,
                byte_lookup,
                expected,
            )
            if start < 0 or end <= start:
                continue
            quotations.append(
                {
                    "start_char": start,
                    "end_char": end,
                    "text": body.text[start:end] or expected,
                    "speaker_cluster_id": str(row.get("char_id") or ""),
                    "speaker_text": str(row.get("mention_phrase") or ""),
                }
            )

        clusters: dict[str, list[str]] = {}
        types: dict[str, str] = {}
        for entity in entities:
            cid = entity["cluster_id"]
            if not cid:
                continue
            clusters.setdefault(cid, []).append(entity["text"])
            if entity["entity_type"]:
                types[cid] = entity["entity_type"]
        for cid, values in aliases.items():
            clusters.setdefault(cid, []).extend(values)
        entity_clusters = [
            {
                "cluster_id": cid,
                "canonical": max(
                    list(dict.fromkeys(values)),
                    key=lambda value: (bool(" " in value), len(value)),
                    default=cid,
                ),
                "aliases": list(dict.fromkeys(values)),
                "entity_type": types.get(cid, ""),
            }
            for cid, values in clusters.items()
        ]
        events: list[dict[str, Any]] = []
        if body.include_events:
            for row in tokens:
                if str(row.get("event") or "").upper() != "EVENT":
                    continue
                token_id = _int(row, "token_ID_within_document", "tokenId", "token_ID")
                start, end = _token_span(
                    tokens,
                    token_id,
                    token_id,
                    body.text,
                    boundaries,
                    byte_lookup,
                    str(row.get("word") or ""),
                )
                if start < 0 or end <= start:
                    continue
                events.append(
                    {
                        "token_id": token_id,
                        "start_char": start,
                        "end_char": end,
                        "text": body.text[start:end] or str(row.get("word") or ""),
                        "lemma": str(row.get("lemma") or ""),
                    }
                )

        return {
            "status": "ok",
            "provider": "booknlp",
            "provider_version": importlib.metadata.version("booknlp"),
            "model": "custom-approved-artifacts",
            "model_artifacts": _artifact_manifest(),
            "configuration": {
                "pipeline": "entity,quote,coref,event" if body.include_events else "entity,quote,coref",
                "pronominal_coref_only": True,
                "profile": body.profile,
            },
            "capabilities": [
                "entities",
                "coreference",
                "quotations",
                "speaker_attribution",
                *(["events"] if body.include_events else []),
            ],
            "entities": entities,
            "entity_clusters": entity_clusters,
            "quotations": quotations,
            "characters": characters,
            "events": events,
        }

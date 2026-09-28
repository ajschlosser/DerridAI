# Copyright 2026 Aaron John Schlosser, PhD.
"""Isolated BookNLP adapter for DerridAI document intelligence.

The worker never downloads model weights.  BookNLP is constructed in custom-model
mode only after all configured artifacts exist.  Its native files are normalized
into a small provider-neutral JSON response; DerridAI remains responsible for
Record/source identity, evidence, review authority, and semantic interpretation.
"""

from __future__ import annotations

import csv
import importlib.metadata
import json
import os
import tempfile
import threading
from bisect import bisect_right
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


def _paths(include_events: bool) -> dict[str, str]:
    required = {
        "entity_model_path": os.environ.get("BOOKNLP_ENTITY_MODEL", ""),
        "coref_model_path": os.environ.get("BOOKNLP_COREF_MODEL", ""),
        "quote_attribution_model_path": os.environ.get("BOOKNLP_QUOTE_MODEL", ""),
    }
    if include_events:
        required["event_model_path"] = os.environ.get("BOOKNLP_EVENT_MODEL", "")
    return required


def _missing_models(include_events: bool = False) -> list[str]:
    return [
        name
        for name, value in _paths(include_events).items()
        if not value or not Path(value).is_file()
    ]


def _pipeline(include_events: bool) -> Any:
    key = "entity,quote,coref,event" if include_events else "entity,quote,coref"
    if key in _models:
        return _models[key]
    missing = _missing_models(include_events)
    if missing:
        raise RuntimeError("Missing approved BookNLP model artifact(s): " + ", ".join(missing))
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


def _byte_map(text: str) -> tuple[list[int], dict[int, int]]:
    boundaries = [0]
    lookup = {0: 0}
    total = 0
    for index, char in enumerate(text, start=1):
        total += len(char.encode("utf-8"))
        boundaries.append(total)
        lookup[total] = index
    return boundaries, lookup


def _to_char(offset: int, boundaries: list[int], lookup: dict[int, int]) -> int:
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
    byte_start = min(_int(row, "byte_onset", "byte_start", default=0) for row in selected)
    byte_end = max(_int(row, "byte_offset", "byte_end", default=byte_start) for row in selected)
    start = _to_char(byte_start, boundaries, lookup)
    end = _to_char(byte_end, boundaries, lookup)
    expected = expected_text.strip()
    if expected:
        broad_start = max(0, start - 2)
        broad_end = min(len(text), end + 2)
        local = text[broad_start:broad_end].find(expected)
        if local >= 0:
            start = broad_start + local
            end = start + len(expected)
    return start, max(start, end)


def _book_aliases(path: Path) -> dict[str, list[str]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    characters = payload.get("characters") if isinstance(payload, dict) else None
    if not isinstance(characters, list):
        return {}
    out: dict[str, list[str]] = {}
    for character in characters:
        if not isinstance(character, dict):
            continue
        cid = str(character.get("id") or character.get("char_id") or character.get("coref") or "")
        if not cid:
            continue
        names: list[str] = []
        for key in ("proper", "common", "pronoun"):
            section = character.get(key)
            values = section if isinstance(section, list) else []
            for item in values:
                if isinstance(item, dict):
                    value = item.get("phrase") or item.get("text") or item.get("name")
                else:
                    value = item
                if str(value or "").strip():
                    names.append(str(value).strip())
        out[cid] = list(dict.fromkeys(names))
    return out


@app.get("/health")
def health() -> dict[str, Any]:
    missing = _missing_models(False)
    return {
        "ready": not missing,
        "provider": "booknlp",
        "version": importlib.metadata.version("booknlp"),
        "missing_model_artifacts": missing,
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
        aliases = _book_aliases(out / f"{book_id}.book")
        boundaries, byte_lookup = _byte_map(body.text)

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

        return {
            "status": "ok",
            "provider": "booknlp",
            "provider_version": importlib.metadata.version("booknlp"),
            "model": "custom-approved-artifacts",
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
            "characters": [
                {"cluster_id": cid, "aliases": values}
                for cid, values in aliases.items()
            ],
        }

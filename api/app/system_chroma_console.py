# Copyright 2026 Aaron John Schlosser, PhD.
"""Validated, read-only CLI-style access to DerridAI's internal Chroma collections."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any

from .chroma_store import ChromaStore


_MAX_GET = 200
_MAX_QUERY = 100
_ALLOWED_GET_INCLUDE = {"documents", "metadatas", "embeddings"}
_ALLOWED_QUERY_INCLUDE = {"documents", "metadatas", "embeddings", "distances"}


@dataclass(frozen=True)
class ParsedSystemChromaCommand:
    verb: str
    collection: str
    options: dict[str, Any]


def _json_object(raw: str, flag: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{flag} must be valid JSON: {exc.msg}.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{flag} must be a JSON object.")
    return value


def _json_string_list(raw: str, flag: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{flag} must be a valid JSON array: {exc.msg}.") from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{flag} must be a JSON array of strings.")
    return list(dict.fromkeys(value))


def _integer(raw: str, flag: str, *, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{flag} must be an integer.") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{flag} must be between {minimum} and {maximum}.")
    return value


def _take(tokens: list[str], index: int, flag: str) -> tuple[str, int]:
    if index + 1 >= len(tokens):
        raise ValueError(f"{flag} requires a value.")
    return tokens[index + 1], index + 2


def parse_system_chroma_command(command: str) -> ParsedSystemChromaCommand:
    """Parse a deliberately small read-only Chroma command language.

    JSON arguments should be quoted just as they would be in a shell, for example:
    get derridai_metadata_exemplars --where '{"field_name":"speaker"}' --limit 20
    query derridai_metadata_exemplars --text "responsibility to the Other" --n-results 8
    """

    try:
        tokens = shlex.split(str(command or "").strip())
    except ValueError as exc:
        raise ValueError(f"Could not parse command: {exc}.") from exc
    if len(tokens) < 2:
        raise ValueError("Use: get <collection> ... or query <collection> ...")
    verb = tokens[0].casefold()
    if verb not in {"get", "query"}:
        raise ValueError("Only read-only 'get' and 'query' commands are supported.")
    collection = tokens[1].strip()
    if not collection:
        raise ValueError("A collection name is required.")

    options: dict[str, Any] = {}
    index = 2
    while index < len(tokens):
        flag = tokens[index]
        if not flag.startswith("--"):
            raise ValueError(f"Unexpected argument {flag!r}; options must start with --.")
        raw, index = _take(tokens, index, flag)
        if flag == "--where":
            options["where"] = _json_object(raw, flag)
        elif flag == "--where-document":
            options["where_document"] = _json_object(raw, flag)
        elif flag == "--ids":
            options["ids"] = _json_string_list(raw, flag)
        elif flag == "--include":
            values = [part.strip() for part in raw.split(",") if part.strip()]
            allowed = _ALLOWED_GET_INCLUDE if verb == "get" else _ALLOWED_QUERY_INCLUDE
            invalid = sorted(set(values) - allowed)
            if invalid:
                raise ValueError(f"{flag} contains unsupported values: {', '.join(invalid)}.")
            options["include"] = values
        elif flag == "--limit" and verb == "get":
            options["limit"] = _integer(raw, flag, minimum=1, maximum=_MAX_GET)
        elif flag == "--offset" and verb == "get":
            options["offset"] = _integer(raw, flag, minimum=0, maximum=1_000_000)
        elif flag == "--text" and verb == "query":
            if not raw.strip():
                raise ValueError("--text cannot be empty.")
            options["text"] = raw
        elif flag == "--n-results" and verb == "query":
            options["n_results"] = _integer(raw, flag, minimum=1, maximum=_MAX_QUERY)
        else:
            raise ValueError(f"{flag} is not valid for {verb}.")
    if verb == "query" and not options.get("text"):
        raise ValueError("query requires --text.")
    return ParsedSystemChromaCommand(verb=verb, collection=collection, options=options)


def _system_collection(store: ChromaStore, name: str):
    collection = store.client.get_collection(name=name)
    metadata = dict(getattr(collection, "metadata", None) or {})
    if not (
        bool(metadata.get("derridai_hidden_system_collection"))
        or bool(metadata.get("derridai_system_collection"))
    ):
        raise ValueError("The console may query only DerridAI system collections.")
    return collection


def list_system_chroma_collections(store: ChromaStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in store.client.list_collections():
        name = str(item.name if hasattr(item, "name") else item)
        try:
            collection = store.client.get_collection(name=name)
        except Exception:
            continue
        metadata = dict(getattr(collection, "metadata", None) or {})
        if not (
            bool(metadata.get("derridai_hidden_system_collection"))
            or bool(metadata.get("derridai_system_collection"))
        ):
            continue
        rows.append({
            "name": name,
            "count": int(collection.count()),
            "derived": bool(metadata.get("derridai_derived")),
            "role": str(metadata.get("derridai_collection_role") or "system"),
        })
    return sorted(rows, key=lambda item: item["name"])


def explain_system_chroma_command(parsed: ParsedSystemChromaCommand) -> str:
    options = parsed.options
    filters: list[str] = []
    if options.get("ids"):
        filters.append(f"only {len(options['ids'])} specified ID(s)")
    if options.get("where"):
        filters.append("a metadata filter")
    if options.get("where_document"):
        filters.append("a document-content filter")
    qualifier = f" with {' and '.join(filters)}" if filters else ""
    if parsed.verb == "get":
        limit = int(options.get("limit") or 25)
        offset = int(options.get("offset") or 0)
        return (
            f"Read up to {limit} stored document(s) from system collection "
            f"'{parsed.collection}' starting at offset {offset}{qualifier}. "
            "This is read-only and will not change embeddings or metadata."
        )
    count = int(options.get("n_results") or 10)
    return (
        f"Embed the supplied query text with the collection's configured embedding "
        f"provider and return up to {count} nearest document(s) from system collection "
        f"'{parsed.collection}'{qualifier}. This is read-only."
    )


def validate_system_chroma_command(store: ChromaStore, command: str) -> dict[str, Any]:
    parsed = parse_system_chroma_command(command)
    collection = _system_collection(store, parsed.collection)
    provider, model = store._embedding_spec(collection)
    if parsed.verb == "query" and provider == "precomputed":
        raise ValueError(
            "This collection uses precomputed vectors, so text similarity queries cannot "
            "create a compatible query vector. Use get/document filters instead."
        )
    return {
        "valid": True,
        "verb": parsed.verb,
        "collection": parsed.collection,
        "options": parsed.options,
        "embedding_provider": provider,
        "embedding_model": model,
        "explanation": explain_system_chroma_command(parsed),
    }


def execute_system_chroma_command(store: ChromaStore, command: str) -> dict[str, Any]:
    validation = validate_system_chroma_command(store, command)
    parsed = parse_system_chroma_command(command)
    collection = _system_collection(store, parsed.collection)
    options = dict(parsed.options)
    if parsed.verb == "get":
        kwargs: dict[str, Any] = {
            "limit": int(options.get("limit") or 25),
            "offset": int(options.get("offset") or 0),
            "include": options.get("include") or ["documents", "metadatas"],
        }
        for key in ("ids", "where", "where_document"):
            if options.get(key) is not None:
                kwargs[key] = options[key]
        result = collection.get(**kwargs)
    else:
        provider, model = store._embedding_spec(collection)
        query_vector = store.embeddings.embed_query(
            str(options["text"]),
            provider=provider,
            model=model,
        )
        kwargs = {
            "query_embeddings": [query_vector],
            "n_results": min(int(options.get("n_results") or 10), max(1, int(collection.count()))),
            "include": options.get("include") or ["documents", "metadatas", "distances"],
        }
        for key in ("where", "where_document"):
            if options.get(key) is not None:
                kwargs[key] = options[key]
        result = collection.query(**kwargs)
    return {
        **validation,
        "result": result,
    }

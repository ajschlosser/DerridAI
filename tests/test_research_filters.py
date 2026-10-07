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

from __future__ import annotations

import pytest
from app.chroma_store import ChromaStore
from app.models import RAGRunRequest, ResearchFilterPlan
from app.research_filters import (
    combine_metadata_filters,
    metadata_filter_fields,
    normalize_document_filter,
    normalize_metadata_filter,
)
from pydantic import ValidationError


def test_metadata_filter_accepts_nested_chroma_subset() -> None:
    raw = {
        "$and": [
            {"work": {"$eq": "Of Grammatology"}},
            {
                "$or": [
                    {"page_start": {"$gte": 100}},
                    {"speaker": {"$in": ["Derrida", "Levinas"]}},
                ]
            },
        ]
    }

    normalized = normalize_metadata_filter(raw)

    assert normalized == raw
    assert metadata_filter_fields(normalized) == {"work", "page_start", "speaker"}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"work": "A", "speaker": "B"}, "exactly one"),
        ({"$and": [{"work": "A"}]}, "at least two"),
        ({"page_start": {"$gte": True}}, "numeric"),
        ({"speaker": {"$in": []}}, "non-empty"),
        ({"speaker": {"$in": ["Derrida", 1]}}, "same-type"),
        ({"speaker": {"$contains": "Derrida"}}, "unsupported operator"),
    ],
)
def test_metadata_filter_rejects_ambiguous_or_unsupported_shapes(value, message) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_metadata_filter(value)


def test_document_filter_supports_contains_negation_and_boolean_groups() -> None:
    raw = {
        "$and": [
            {"$contains": "trace"},
            {"$not_contains": "Heidegger"},
        ]
    }

    assert normalize_document_filter(raw) == raw


def test_combining_scope_filters_preserves_both_constraints() -> None:
    combined = combine_metadata_filters(
        {"work": {"$ne": "Totality and Infinity"}},
        {"work": {"$in": ["Of Grammatology"]}},
    )

    assert combined == {
        "$and": [
            {"work": {"$ne": "Totality and Infinity"}},
            {"work": {"$in": ["Of Grammatology"]}},
        ]
    }


def test_rag_filter_plan_validates_before_job_execution() -> None:
    request = RAGRunRequest(
        prompt="What is the trace?",
        source_collection="corpus",
        filter_plan={
            "metadata_filter": {"work": {"$eq": "Of Grammatology"}},
            "document_filter": {"$not_contains": "editorial note"},
            "source": "explicit",
        },
    )

    assert isinstance(request.filter_plan, ResearchFilterPlan)
    assert request.filter_plan.metadata_filter == {"work": {"$eq": "Of Grammatology"}}

    with pytest.raises(ValidationError, match="requires a numeric value"):
        RAGRunRequest(
            prompt="What is the trace?",
            source_collection="corpus",
            filter_plan={"metadata_filter": {"page_start": {"$gte": "late"}}},
        )


def test_filter_plan_survives_request_roundtrip_and_defaults_to_none() -> None:
    request = RAGRunRequest(
        prompt="q",
        source_collection="corpus",
        filter_plan={"metadata_filter": {"work": "A"}, "source": "explicit"},
    )
    restored = RAGRunRequest(**request.model_dump())
    assert restored.filter_plan == request.filter_plan
    legacy = request.model_dump()
    legacy.pop("filter_plan")
    assert RAGRunRequest(**legacy).filter_plan is None


class _CaptureCollection:
    def __init__(self) -> None:
        self.metadata = {"hnsw:space": "cosine"}
        self.last_get = None
        self.get_calls = []
        self.last_query = None

    def count(self) -> int:
        return 1

    def query(self, **kwargs):
        self.last_query = kwargs
        return {
            "ids": [["r1"]],
            "documents": [["The trace is not a presence."]],
            "metadatas": [[{"_record_id": "r1", "work": "Of Grammatology"}]],
            "distances": [[0.1]],
            "embeddings": [[[0.2, 0.3]]],
        }

    def get(self, **kwargs):
        self.last_get = kwargs
        self.get_calls.append(kwargs)
        return {
            "ids": ["r1"],
            "documents": ["The trace is not a presence."],
            "metadatas": [{"_record_id": "r1", "work": "Of Grammatology"}],
        }


class _Embeddings:
    def embed_query(self, _query, *, provider=None, model=None):
        return [0.1, 0.2]


def _capture_store(collection: _CaptureCollection) -> ChromaStore:
    store = object.__new__(ChromaStore)
    store._collection = lambda _name: collection
    store._embedding_spec = lambda _collection: ("chroma", None)
    store.embeddings = _Embeddings()
    return store


def test_chroma_candidate_generation_receives_both_filter_channels() -> None:
    collection = _CaptureCollection()
    store = _capture_store(collection)
    where = {"work": {"$eq": "Of Grammatology"}}
    where_document = {"$contains": "trace"}

    semantic = store.semantic_candidates(
        "corpus",
        "trace",
        4,
        where=where,
        where_document=where_document,
    )

    assert [item["record"]["record_id"] for item in semantic] == ["r1"]
    assert collection.last_query["where"] == where
    assert collection.last_query["where_document"] == where_document

    lexical = store.lexical_search(
        "corpus",
        "trace",
        4,
        where=where,
        where_document=where_document,
    )

    assert [item["record"]["record_id"] for item in lexical] == ["r1"]
    assert any(call.get("where") == where for call in collection.get_calls)
    assert any(
        call.get("where_document") == where_document
        for call in collection.get_calls
    )


class _PagedLexicalCollection:
    def __init__(self, count: int = 350) -> None:
        self.metadata = {"hnsw:space": "cosine"}
        self.calls: list[dict] = []
        self.rows = [
            (
                f"r{index}",
                (
                    "trace trace différance"
                    if index == count - 1
                    else f"ordinary passage {index}"
                ),
                {
                    "_record_id": f"r{index}",
                    "work": "Of Grammatology",
                    "document_author": "Jacques Derrida",
                    # Deliberately large irrelevant JSON metadata. The lexical
                    # scan must not decode it for every candidate.
                    "updates": "__json__:" + ("[{\"field\":\"x\"}]" * 200),
                },
            )
            for index in range(count)
        ]

    def count(self) -> int:
        return len(self.rows)

    def get(self, *, ids=None, include=None, limit=None, offset=0, **kwargs):
        self.calls.append(
            {
                "ids": list(ids) if ids is not None else None,
                "include": include,
                "limit": limit,
                "offset": offset,
                **kwargs,
            }
        )
        if ids is not None:
            wanted = set(ids)
            rows = [row for row in self.rows if row[0] in wanted]
        else:
            stop = offset + int(limit or len(self.rows))
            rows = self.rows[offset:stop]
        return {
            "ids": [row[0] for row in rows],
            "documents": [row[1] for row in rows],
            "metadatas": [row[2] for row in rows],
        }


def test_lexical_search_pages_candidates_and_decodes_only_final_results(
    monkeypatch,
) -> None:
    from app import chroma_store as chroma_store_module

    collection = _PagedLexicalCollection()
    store = object.__new__(ChromaStore)
    store._collection = lambda _name: collection

    original_decode_metadata = chroma_store_module.decode_metadata
    decoded = []

    def tracked_decode(metadata):
        decoded.append(metadata)
        return original_decode_metadata(metadata)

    monkeypatch.setattr(chroma_store_module, "decode_metadata", tracked_decode)

    result = store.lexical_search("corpus", "trace différance", 4)

    assert result[0]["id"] == f"r{len(collection.rows) - 1}"
    scan_calls = [call for call in collection.calls if call["ids"] is None]
    assert len(scan_calls) > 1
    assert all(call["limit"] is not None for call in scan_calls)
    assert all(call["limit"] <= 512 for call in scan_calls)
    assert all(call["include"] == ["documents", "metadatas"] for call in scan_calls)

    final_calls = [call for call in collection.calls if call["ids"] is not None]
    assert len(final_calls) == 1
    assert len(final_calls[0]["ids"]) <= 4
    assert len(decoded) <= 4


# --- Phase 2: preview endpoint -------------------------------------------------


class _PreviewStore:
    def __init__(self, stores):
        self._stores = stores
        self.writes = 0

    def list_stores(self):
        return self._stores


def _preview(monkeypatch, stores, **body):
    from app.routers import research_filters as routes

    fake = _PreviewStore(stores)
    monkeypatch.setattr(routes, "store", fake)
    request = routes.ResearchFilterPreviewRequest(collection="corpus", **body)
    return routes.preview_research_filter(request), fake


_CORPUS = [{"name": "corpus", "filter_fields": ["work", "page_start"]}]


def test_preview_explains_valid_plan_and_reports_fields(monkeypatch) -> None:
    result, _ = _preview(
        monkeypatch,
        _CORPUS,
        metadata_filter={
            "$and": [{"work": "Of Grammatology"}, {"page_start": {"$gte": 100}}]
        },
        document_filter={"$contains": "trace"},
    )
    assert result["valid"] is True
    assert result["fields_referenced"] == ["page_start", "work"]
    assert result["collection_filter_fields"] == ["page_start", "work"]
    group = result["explanation"]["metadata"]
    assert group["operator"] == "and" and len(group["children"]) == 2
    assert result["explanation"]["document"]["operator"] == "$contains"


def test_preview_reports_unknown_fields_and_malformed_filters(monkeypatch) -> None:
    unknown, _ = _preview(monkeypatch, _CORPUS, metadata_filter={"speaker": "Derrida"})
    assert unknown["valid"] is False
    assert unknown["unsupported_fields"] == ["speaker"]
    assert unknown["errors"][0]["code"] == "unknown_field"

    malformed, _ = _preview(
        monkeypatch, _CORPUS, metadata_filter={"page_start": {"$gte": "late"}}
    )
    assert malformed["valid"] is False
    assert malformed["errors"][0]["code"] == "invalid_filter"
    assert "numeric" in malformed["errors"][0]["params"]["message"]


def test_preview_warns_when_collection_declares_no_filter_fields(monkeypatch) -> None:
    result, _ = _preview(
        monkeypatch, [{"name": "corpus"}], metadata_filter={"work": "A"}
    )
    assert result["valid"] is True
    assert result["warnings"][0]["code"] == "collection_declares_no_filter_fields"


def test_preview_rejects_missing_and_system_collections(monkeypatch) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as missing:
        _preview(monkeypatch, [], metadata_filter={"work": "A"})
    assert missing.value.status_code == 404

    system = [
        {
            "name": "corpus",
            "metadata": {"derridai_system_collection": "response_cache"},
            "filter_fields": ["work"],
        }
    ]
    with pytest.raises(HTTPException) as hidden:
        _preview(monkeypatch, system, metadata_filter={"work": "A"})
    assert hidden.value.status_code == 404


def test_preview_route_is_available_to_researchers_with_run_capability() -> None:
    from app.route_policy import non_admin_route_allowed

    assert non_admin_route_allowed("researcher", "/api/research/filters/preview", "POST")
    assert not non_admin_route_allowed("researcher", "/api/research/filters/preview", "GET")


# --- Phase 4: work/author inventory for natural-language scope ---------------


class _InventoryStore(_PreviewStore):
    def work_stats(self, name):
        assert name == "corpus"
        return [
            {"work": "Of Grammatology", "document_author": "Jacques Derrida"},
            {"work": "Being and Time", "document_author": "Martin Heidegger"},
            {"work": ""},
        ]


def test_inventory_lists_names_only_and_is_bounded(monkeypatch) -> None:
    from app.routers import research_filters as routes

    monkeypatch.setattr(routes, "store", _InventoryStore(_CORPUS))
    result = routes.research_filter_inventory(
        routes.ResearchFilterInventoryRequest(collection="corpus")
    )
    assert result == {
        "works": [
            {"work": "Being and Time", "authors": ["Martin Heidegger"]},
            {"work": "Of Grammatology", "authors": ["Jacques Derrida"]},
        ],
        "truncated": False,
    }
    monkeypatch.setattr(routes, "INVENTORY_MAX_WORKS", 1)
    capped = routes.research_filter_inventory(
        routes.ResearchFilterInventoryRequest(collection="corpus")
    )
    assert len(capped["works"]) == 1 and capped["truncated"] is True


def test_inventory_rejects_hidden_collections_and_is_researcher_post_only(monkeypatch) -> None:
    from app.route_policy import non_admin_route_allowed
    from app.routers import research_filters as routes
    from fastapi import HTTPException

    hidden = [{"name": "corpus", "metadata": {"derridai_system_collection": "response_cache"}}]
    monkeypatch.setattr(routes, "store", _InventoryStore(hidden))
    with pytest.raises(HTTPException) as exc:
        routes.research_filter_inventory(routes.ResearchFilterInventoryRequest(collection="corpus"))
    assert exc.value.status_code == 404
    assert non_admin_route_allowed("researcher", "/api/research/filters/inventory", "POST")
    assert not non_admin_route_allowed("researcher", "/api/research/filters/inventory", "GET")

# Copyright 2026 Aaron John Schlosser, PhD.
"""Document intelligence GraphQL reads share the authoritative REST/domain services."""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import httpx  # noqa: E402
from app import main  # noqa: E402
from app.auth import auth_store  # noqa: E402
from app.celf_queries import document_intelligence_reads, source_documents as document_queries  # noqa: E402
from app.celf_queries.access import AccessContext, AccessDenied  # noqa: E402
from app.corpus_builder import PdfCorpusRepository  # noqa: E402
from app.routers import corpus as corpus_routes  # noqa: E402
from app.routers import sources as source_routes  # noqa: E402

USERS = {
    "admin-cookie": SimpleNamespace(id=1, username="root", role="admin", active=True),
    "researcher-cookie": SimpleNamespace(id=2, username="reader", role="researcher", active=True),
}


class BuildIntelligence:
    def document_intelligence(self, build_id: str):
        if build_id == "build-empty":
            return {}
        if build_id != "build-1":
            raise KeyError(build_id)
        return {
            "version": 1,
            "status": "ok",
            "profile": "scholarly",
            "selected_provider": "auto",
            "provider": "spacy",
            "provider_version": "3.8",
            "model": "en_core_web_sm",
            "capabilities": ["entities"],
            "model_artifacts": [
                {"role": "ner", "name": "en_core_web_sm", "sha256": "ab" * 32}
            ],
            "configuration": {"include_events": False},
            "text_sha256": "11" * 32,
            "current_text_sha256": "11" * 32,
            "text_length": 100,
            "stale": False,
            "warnings": [],
            "record_spans": [
                {
                    "record_id": "r1",
                    "record_revision": 2,
                    "start": 0,
                    "end": 100,
                    "text_sha256": "22" * 32,
                    "source_unit_ids": ["b1"],
                }
            ],
            "entity_clusters": [
                {
                    "cluster_id": "person:derrida",
                    "canonical": "Jacques Derrida",
                    "aliases": ["Derrida"],
                    "entity_type": "PERSON",
                }
            ],
            "entities": [
                {
                    "cluster_id": "person:derrida",
                    "start_char": 0,
                    "end_char": 15,
                    "text": "Jacques Derrida",
                    "mention_type": "named",
                    "entity_type": "PERSON",
                }
            ],
            "quotations": [],
            "characters": [],
            "events": [],
        }


class CaptureLinks:
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id

    def links_for_sources(self, source_ids=None):
        if source_ids and self.source_id not in source_ids:
            return {}
        return {
            self.source_id: [
                {
                    "capture_id": "capture-1",
                    "candidate_id": "candidate-1",
                    "provider": "gutenberg",
                    "provider_item_id": "123",
                    "discovery_method": "catalog",
                    "discovered_at": "2026-09-28T00:00:00+00:00",
                    "acquired_at": "2026-09-28T00:01:00+00:00",
                    "author_name": "Jacques Derrida",
                }
            ]
        }


@pytest.fixture(autouse=True)
def sessions(monkeypatch):
    monkeypatch.setattr(auth_store, "user_for_session", lambda cookie: USERS.get(cookie or ""))


def _call(method: str, path: str, *, cookie: str = "admin-cookie", **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://t",
            cookies={"derridai_session": cookie},
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run())


def gql(query: str, variables: dict | None = None, *, cookie: str = "admin-cookie"):
    return _call(
        "POST",
        "/api/graphql",
        cookie=cookie,
        json={"query": query, "variables": variables or {}},
    )


@pytest.fixture()
def build_intelligence(monkeypatch):
    service = BuildIntelligence()
    monkeypatch.setattr(document_intelligence_reads, "pdf_corpus_builds", service)
    monkeypatch.setattr(corpus_routes, "pdf_corpus_builds", service)
    return service


@pytest.fixture()
def source_repo(tmp_path, monkeypatch):
    repo = PdfCorpusRepository(tmp_path / "corpus")
    asset = repo.save_asset(
        (
            b"Of Hospitality\n\n"
            b"The threshold is not a simple door.\n\n"
            b"A second paragraph keeps the source unit boundary visible."
        ),
        filename="hospitality.txt",
        catalog_metadata={
            "provider": "gutenberg",
            "provider_item_id": "123",
            "title": "Of Hospitality",
            "document_author": "Jacques Derrida",
        },
    )
    links = CaptureLinks(asset["asset_id"])
    monkeypatch.setattr(document_queries, "pdf_corpus_repository", repo)
    monkeypatch.setattr(document_queries, "capture_store", links)
    monkeypatch.setattr(source_routes, "pdf_corpus_repository", repo)
    monkeypatch.setattr(source_routes, "capture_store", links)
    monkeypatch.setattr(corpus_routes, "pdf_corpus_repository", repo)
    return repo, asset


SOURCE_QUERY = """
query SourceDocumentIntelligence($id: String!) {
  source_document(source_document_id: $id) {
    source_document_id
    sha256
    filename
    media_kind
    source_unit_count
    catalog_metadata
    initial_metadata
    extraction_provenance
    captures {
      capture_id
      provider
      provider_item_id
      author_name
    }
    builds {
      build_id
      status
      record_count
    }
    pages(limit: 5) {
      total
      items {
        physical_page
        printed_page_label
        extraction_method
        block_ids
      }
    }
    source_units(limit: 2) {
      total
      offset
      limit
      items {
        source_unit_id
        page
        type
        text
        extraction_method
        confidence
      }
    }
  }
}
"""


def test_source_document_graphql_reads_identity_provenance_and_bounded_units(source_repo):
    _repo, asset = source_repo
    response = gql(SOURCE_QUERY, {"id": asset["asset_id"]})
    assert response.status_code == 200
    body = response.json()
    assert "errors" not in body, body

    source = body["data"]["source_document"]
    assert source["source_document_id"] == asset["asset_id"]
    assert source["sha256"] == asset["sha256"]
    assert source["filename"] == "hospitality.txt"
    assert source["source_unit_count"] == asset["block_count"]
    assert source["catalog_metadata"]["provider"] == "gutenberg"
    assert source["extraction_provenance"]["contract"] == "source-extraction-v2"
    assert source["captures"][0]["capture_id"] == "capture-1"
    assert source["source_units"]["total"] == asset["block_count"]
    assert 1 <= len(source["source_units"]["items"]) <= 2
    assert all(item["source_unit_id"] for item in source["source_units"]["items"])


def test_source_detail_rest_and_graphql_share_the_same_document_read(source_repo):
    _repo, asset = source_repo
    rest = _call("GET", f"/api/corpus/sources/{asset['asset_id']}")
    assert rest.status_code == 200
    graph = gql(SOURCE_QUERY, {"id": asset["asset_id"]}).json()["data"]["source_document"]

    detail = rest.json()
    assert detail["asset_id"] == graph["source_document_id"]
    assert detail["sha256"] == graph["sha256"]
    assert detail["filename"] == graph["filename"]
    assert detail["block_count"] == graph["source_unit_count"]
    assert detail["catalog_metadata"] == graph["catalog_metadata"]
    assert detail["captures"] == [
        {
            "capture_id": "capture-1",
            "candidate_id": "candidate-1",
            "provider": "gutenberg",
            "provider_item_id": "123",
            "discovery_method": "catalog",
            "discovered_at": "2026-09-28T00:00:00+00:00",
            "acquired_at": "2026-09-28T00:01:00+00:00",
            "author_name": "Jacques Derrida",
        }
    ]


def test_source_unit_rest_and_graphql_share_paging_semantics(source_repo):
    _repo, asset = source_repo
    rest = _call(
        "GET",
        f"/api/pdf/assets/{asset['asset_id']}/blocks",
        params={"offset": 0, "limit": 1},
    )
    assert rest.status_code == 200
    rest_page = rest.json()

    query = """
    query OneUnit($id: String!) {
      source_document(source_document_id: $id) {
        source_units(offset: 0, limit: 1) {
          total offset limit
          items { source_unit_id text }
        }
      }
    }
    """
    graph_page = gql(query, {"id": asset["asset_id"]}).json()["data"]["source_document"]["source_units"]
    assert graph_page["total"] == rest_page["total"]
    assert graph_page["offset"] == rest_page["offset"]
    assert graph_page["limit"] == rest_page["limit"]
    assert graph_page["items"][0]["source_unit_id"] == rest_page["items"][0]["block_id"]
    assert graph_page["items"][0]["text"] == rest_page["items"][0]["text"]


def test_document_intelligence_is_admin_only(source_repo):
    _repo, asset = source_repo
    response = gql(SOURCE_QUERY, {"id": asset["asset_id"]}, cookie="researcher-cookie")
    assert response.status_code == 200
    error = response.json()["errors"][0]
    assert error["extensions"]["code"] == "FORBIDDEN"

    with pytest.raises(AccessDenied):
        document_queries.source_document(
            AccessContext(username="reader", role="researcher", user_id=2),
            asset["asset_id"],
        )

DOCUMENT_INTELLIGENCE_QUERY = """
query BuildDocumentIntelligence($id: String!) {
  corpus_build(build_id: $id) {
    document_intelligence {
      version
      status
      profile
      selected_provider
      provider
      provider_version
      model
      capabilities
      text_sha256
      current_text_sha256
      text_length
      stale
      warnings
      model_artifacts { role name sha256 }
      record_spans { record_id record_revision start end text_sha256 source_unit_ids }
      entity_clusters { cluster_id canonical aliases entity_type }
      entities { cluster_id start_char end_char text mention_type entity_type }
      quotations { start_char end_char text speaker_cluster_id speaker_text }
      characters
      events
    }
  }
}
"""


def test_build_document_intelligence_graphql_matches_rest_read(build_intelligence):
    rest = _call("GET", "/api/pdf/corpus-builds/build-1/document-intelligence")
    assert rest.status_code == 200

    response = gql(DOCUMENT_INTELLIGENCE_QUERY, {"id": "build-1"})
    assert response.status_code == 200
    body = response.json()
    assert "errors" not in body, body
    value = body["data"]["corpus_build"]["document_intelligence"]

    assert value["status"] == rest.json()["status"] == "ok"
    assert value["profile"] == rest.json()["profile"] == "scholarly"
    assert value["provider"] == rest.json()["provider"] == "spacy"
    assert value["stale"] is False
    assert value["entity_clusters"][0]["canonical"] == "Jacques Derrida"
    assert value["record_spans"][0]["source_unit_ids"] == ["b1"]


def test_build_document_intelligence_graphql_is_null_before_analysis(build_intelligence):
    response = gql(DOCUMENT_INTELLIGENCE_QUERY, {"id": "build-empty"})
    assert response.status_code == 200
    body = response.json()
    assert "errors" not in body, body
    assert body["data"]["corpus_build"]["document_intelligence"] is None



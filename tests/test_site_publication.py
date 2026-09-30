# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest

from app import site_publication
from app.chroma_store import ChromaStore


def _record(record_id: str = "r1", work: str = "Glas") -> dict:
    return {
        "record_id": record_id,
        "source_document_id": "source-1",
        "source_spans": [
            {
                "source_document_id": "source-1",
                "source_unit_id": f"unit-{record_id}",
                "printed_page": "12",
            }
        ],
        "work": work,
        "document_author": "Jacques Derrida",
        "citation": "Derrida, Jacques. Glas.",
        "speaker": "Derrida",
        "position_holder": "Hegel",
        "text": "A publication-safe passage.",
    }


def _publication_from_index(index_html: str) -> dict:
    match = re.search(
        r'<script id="derridai-publication" type="application/json">(.*?)</script>',
        index_html,
        flags=re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


def test_site_bundle_separates_authoritative_records_from_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {
                "name": store_name,
                "embedding_provider": "profile:embed",
                "embedding_model": "bge-m3:latest",
                "embedding_dimension": 3,
                "distance_metric": "cosine",
                "retrieval_mode": "hybrid",
                "text_field": "text",
                "filter_fields": ["work", "speaker"],
            },
            "records": [
                {"record": _record(), "embedding": [0.1, 0.2, 0.3]},
            ],
        },
    )
    monkeypatch.setattr(
        site_publication.system_store,
        "researcher_profiles",
        lambda: [
            {
                "id": "embed",
                "name": "Lab endpoint",
                "type": "openai",
                "base_url": "https://models.example/v1",
                "model": "chat-model",
                "api_key": "MUST-NOT-LEAK",
            }
        ],
    )

    bundle = site_publication.build_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Glas research site",
        description="A static scholarly research site.",
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        assert set(archive.namelist()) == {"index.html", "derridai-site.js"}
        index_html = archive.read("index.html").decode("utf-8")
        runtime = archive.read("derridai-site.js").decode("utf-8")

    publication = _publication_from_index(index_html)
    assert publication["format"] == "derridai-static-site-v1"
    assert publication["corpus_id"] == "derrida-primary"
    assert publication["works"][0]["work"] == "Glas"
    assert publication["records"][0]["record_id"] == "r1"
    assert "embedding" not in publication["records"][0]
    assert publication["vector_index"]["record_ids"] == ["r1"]
    assert publication["vector_index"]["vectors"] == [[0.1, 0.2, 0.3]]
    assert publication["features"]["semantic_search"] is True
    assert publication["provider_profiles"][0]["id"] == "embed"
    assert "api_key" not in publication["provider_profiles"][0]
    assert "MUST-NOT-LEAK" not in index_html
    assert "Research" in runtime
    assert bundle.record_count == 1
    assert bundle.work_count == 1


def test_site_bundle_blocks_records_that_are_not_publication_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _record()
    invalid.pop("source_spans")
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda _store_name, _works: {
            "store": {"name": "derrida-primary"},
            "records": [{"record": invalid, "embedding": None}],
        },
    )
    monkeypatch.setattr(site_publication.system_store, "researcher_profiles", lambda: [])

    with pytest.raises(ValueError, match="publication-valid"):
        site_publication.build_site_bundle(
            store_name="derrida-primary",
            works=["Glas"],
            title="Invalid",
        )


class _Collection:
    metadata = {}

    def count(self) -> int:
        return 2

    def get(self, **_kwargs):
        return {
            "ids": ["r1", "r2"],
            "documents": ["Text one", "Text two"],
            "metadatas": [
                {
                    "record_id": "r1",
                    "work": "Glas",
                    "source_document_id": "s1",
                    "source_spans": '__json__:[{"source_document_id":"s1","source_unit_id":"u1"}]',
                },
                {
                    "record_id": "r2",
                    "work": "Rogues",
                    "source_document_id": "s2",
                    "source_spans": '__json__:[{"source_document_id":"s2","source_unit_id":"u2"}]',
                },
            ],
            "embeddings": [[1.0, 0.0], [0.0, 1.0]],
        }


class _ProjectionStore:
    def _collection(self, _name: str):
        return _Collection()

    def _public_store(self, _collection):
        return {
            "name": "derrida-primary",
            "embedding_provider": "ollama",
            "embedding_model": "bge-m3:latest",
            "embedding_dimension": 2,
            "distance_metric": "cosine",
        }


def test_vector_projection_exports_only_selected_works_with_existing_embeddings() -> None:
    projection = ChromaStore.export_site_projection(
        _ProjectionStore(),  # type: ignore[arg-type]
        "derrida-primary",
        ["Glas"],
    )
    assert projection["store"]["embedding_dimension"] == 2
    assert len(projection["records"]) == 1
    assert projection["records"][0]["record"]["record_id"] == "r1"
    assert projection["records"][0]["record"]["text"] == "Text one"
    assert projection["records"][0]["embedding"] == [1.0, 0.0]

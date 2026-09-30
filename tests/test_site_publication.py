# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import base64
import io
import json
import struct
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


def _package_from_runtime(runtime: str) -> dict:
    prefix = f"globalThis.{site_publication.PACKAGE_GLOBAL}="
    assert runtime.startswith(prefix)
    payload = runtime[len(prefix) :].split(";\n", 1)[0]
    return json.loads(payload)


def _chunk_records(chunk: dict) -> list[dict]:
    return json.loads(base64.b64decode(chunk["records_b64"]).decode("utf-8"))


def _chunk_vectors(chunk: dict, dimension: int) -> list[list[float]]:
    raw = base64.b64decode(chunk["vectors_b64"])
    count = len(raw) // 4
    values = struct.unpack(f"<{count}f", raw)
    return [
        list(values[offset : offset + dimension])
        for offset in range(0, len(values), dimension)
    ]


def test_site_bundle_is_exactly_two_files_with_progressive_client_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                {"record": _record("r1", "Glas"), "embedding": [0.1, 0.2, 0.3]},
                {"record": _record("r2", "Rogues"), "embedding": [0.4, 0.5, 0.6]},
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
        works=["Glas", "Rogues"],
        title="Derrida research site",
        description="A static scholarly research site.",
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        assert archive.namelist() == ["index.html", "derridai-site.js"]
        index_html = archive.read("index.html").decode("utf-8")
        runtime = archive.read("derridai-site.js").decode("utf-8")

    assert "derridai-publication" not in index_html
    assert "A publication-safe passage." not in index_html
    assert "derridai-site.js" in index_html
    assert "connect-src 'self' http: https:" in index_html

    package = _package_from_runtime(runtime)
    publication = package["manifest"]
    chunks = package["chunks"]

    assert publication["format"] == "derridai-static-site-v2"
    assert publication["corpus_id"] == "derrida-primary"
    assert [work["work"] for work in publication["works"]] == ["Glas", "Rogues"]
    assert publication["features"]["browser_llm"] is False
    assert publication["features"]["external_provider_generation"] is True
    assert publication["features"]["progressive_work_loading"] is True
    assert publication["vector_index"]["dimension"] == 3
    assert publication["vector_index"]["model"] == "bge-m3:latest"
    assert "records" not in publication
    assert "vectors" not in publication["vector_index"]

    assert [chunk["work"] for chunk in chunks] == ["Glas", "Rogues"]
    assert _chunk_records(chunks[0])[0]["record_id"] == "r1"
    assert _chunk_records(chunks[1])[0]["record_id"] == "r2"
    decoded = _chunk_vectors(chunks[0], 3)[0]
    assert decoded == pytest.approx([0.1, 0.2, 0.3])

    assert publication["provider_profiles"][0]["id"] == "embed"
    assert "api_key" not in publication["provider_profiles"][0]
    assert "base_url" not in publication["provider_profiles"][0]
    assert "MUST-NOT-LEAK" not in runtime
    assert "testProviderConnection" in runtime
    assert "OLLAMA_ORIGINS" in runtime
    assert "semantic_provider_fallback" in runtime
    assert bundle.record_count == 2
    assert bundle.work_count == 2


def test_site_chunks_records_and_vectors_by_work() -> None:
    records = [
        _record("g1", "Glas"),
        _record("r1", "Rogues"),
        _record("g2", "Glas"),
    ]
    vectors = [[1.0, 0.0], None, [0.0, 1.0]]

    chunks = site_publication._chunk_publication(
        selected_works=["Glas", "Rogues"],
        records=records,
        vectors=vectors,
        dimension=2,
    )

    assert len(chunks) == 2
    assert [record["record_id"] for record in _chunk_records(chunks[0])] == ["g1", "g2"]
    assert chunks[0]["vector_ids"] == ["g1", "g2"]
    assert _chunk_vectors(chunks[0], 2) == pytest.approx([[1.0, 0.0], [0.0, 1.0]])
    assert [record["record_id"] for record in _chunk_records(chunks[1])] == ["r1"]
    assert chunks[1]["vector_ids"] == []
    assert chunks[1]["vectors_b64"] == ""


def test_site_bundle_blocks_when_a_selected_work_is_not_indexed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda _store_name, _works: {
            "store": {"name": "derrida-primary"},
            "records": [{"record": _record(work="Glas"), "embedding": None}],
        },
    )
    monkeypatch.setattr(site_publication.system_store, "researcher_profiles", lambda: [])

    with pytest.raises(ValueError, match="Missing: Rogues"):
        site_publication.build_site_bundle(
            store_name="derrida-primary",
            works=["Glas", "Rogues"],
            title="Partial export",
        )


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

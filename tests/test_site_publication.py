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


def _package_from_runtime(asset: str) -> dict:
    prefix = f"globalThis.{site_publication.PACKAGE_GLOBAL}="
    assert asset.startswith(prefix)
    payload = asset[len(prefix) :].split(";\n", 1)[0]
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


def test_site_bundle_separates_publication_sdk_and_reference_ui(
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

    bundle = site_publication.build_site_bundle(
        store_name="derrida-primary",
        works=["Glas", "Rogues"],
        title="Derrida research site",
        description="A static scholarly research site.",
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        assert archive.namelist() == ["index.html", "derridai-site.js"]
        index_html = archive.read("index.html").decode("utf-8")
        site_runtime = archive.read("derridai-site.js").decode("utf-8")

    assert "A publication-safe passage." not in index_html
    assert index_html.count("<script ") == 1
    assert 'src="./derridai-site.js"' in index_html
    assert "connect-src 'self' http: https:" in index_html

    package = _package_from_runtime(site_runtime)
    publication = package["manifest"]
    chunks = package["chunks"]

    assert publication["format"] == "derridai-static-site-v4"
    assert publication["corpus_id"] == "derrida-primary"
    assert [work["work"] for work in publication["works"]] == ["Glas", "Rogues"]
    assert publication["features"]["browser_llm"] is False
    assert publication["features"]["derridai_sdk"] is True
    assert publication["features"]["host_supplied_generation"] is True
    assert publication["features"]["direct_provider_endpoints"] is False
    assert publication["features"]["progressive_work_loading"] is True
    assert publication["vector_index"]["dimension"] == 3
    assert publication["vector_index"]["model"] == "bge-m3:latest"
    assert publication["provider_profiles"] == []
    assert "records" not in publication
    assert "vectors" not in publication["vector_index"]

    assert [chunk["work"] for chunk in chunks] == ["Glas", "Rogues"]
    assert _chunk_records(chunks[0])[0]["record_id"] == "r1"
    assert _chunk_records(chunks[1])[0]["record_id"] == "r2"
    decoded = _chunk_vectors(chunks[0], 3)[0]
    assert decoded == pytest.approx([0.1, 0.2, 0.3])

    assert "createClient" in site_runtime
    assert "DerridAI" in site_runtime
    assert "__DERRIDAI_HOST_CAPABILITIES__" in site_runtime
    assert "sdk.createClient" in site_runtime
    assert "OLLAMA_ORIGINS" in site_runtime
    assert "derridai.site.providers." in site_runtime
    assert "site.runtime.save_provider" in site_runtime
    assert "site.runtime.provider_local_help" in site_runtime
    # The shared browser client contains provider adapters, but this publication
    # exports no provider profile, endpoint, or credential unless the publisher
    # explicitly selects one.
    assert publication["provider_profiles"] == []
    assert "https://models.example" not in site_runtime
    assert "MUST-NOT-EXPORT" not in site_runtime
    assert bundle.record_count == 2
    assert bundle.work_count == 2

def test_site_bundle_exports_only_selected_installed_languages_and_safe_provider_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {
                "name": store_name,
                "embedding_provider": "profile:openai-main",
                "embedding_model": "bge-m3:latest",
                "embedding_dimension": 3,
                "distance_metric": "cosine",
            },
            "records": [
                {"record": _record("r1", "Glas"), "embedding": [0.1, 0.2, 0.3]},
            ],
        },
    )
    monkeypatch.setattr(
        site_publication.system_store,
        "list_languages",
        lambda: [
            {"code": "en-US", "name": "English", "flag": "🇺🇸"},
            {"code": "fr-CA", "name": "Français", "flag": "🇨🇦"},
            {"code": "de-DE", "name": "Deutsch", "flag": "🇩🇪"},
        ],
    )
    dictionaries = {
        "en-US": dict(site_publication.EN_US),
        "fr-CA": {**site_publication.EN_US, "site.runtime.search": "Rechercher"},
        "de-DE": {**site_publication.EN_US, "site.runtime.search": "Suchen"},
    }
    monkeypatch.setattr(
        site_publication.system_store,
        "get_language",
        lambda code: {
            "code": code,
            "name": code,
            "flag": "🌐",
            "dictionary": dictionaries[code],
        },
    )
    monkeypatch.setattr(
        site_publication.system_store,
        "researcher_profiles",
        lambda: [
            {
                "id": "openai-main",
                "name": "OpenAI-compatible lab",
                "type": "openai",
                "base_url": "https://models.example.edu/v1",
                "model": "gpt-oss:20b",
                "has_api_key": True,
                "api_key": "MUST-NOT-EXPORT",
            },
            {
                "id": "other",
                "name": "Other",
                "type": "openai",
                "base_url": "https://other.example/v1",
                "model": "other-model",
            },
        ],
    )

    bundle = site_publication.build_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Multilingual site",
        locale="de-DE",
        languages=["de-DE", "fr-CA"],
        provider_profile_ids=["openai-main"],
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        site_runtime = archive.read("derridai-site.js").decode("utf-8")
    package = _package_from_runtime(site_runtime)
    manifest = package["manifest"]

    assert manifest["locale"] == "de-DE"
    assert [item["code"] for item in manifest["languages"]] == ["de-DE", "fr-CA"]
    assert set(manifest["strings"]) == {"de-DE", "fr-CA"}
    assert manifest["strings"]["de-DE"]["site.runtime.search"] == "Suchen"
    assert manifest["strings"]["de-DE"]["site.runtime.site_title"] == site_publication.EN_US["site.runtime.site_title"]
    assert manifest["provider_profiles"] == [
        {
            "id": "openai-main",
            "name": "OpenAI-compatible lab",
            "type": "openai",
            "base_url": "https://models.example.edu/v1",
            "model": "gpt-oss:20b",
            "has_api_key": True,
        }
    ]
    assert "MUST-NOT-EXPORT" not in site_runtime
    assert manifest["features"]["direct_provider_endpoints"] is True
    assert "site.runtime.provider_saved" in site_runtime


def test_site_bundle_rejects_selected_language_with_missing_runtime_translations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {"name": store_name},
            "records": [{"record": _record("r1", "Glas"), "embedding": None}],
        },
    )
    monkeypatch.setattr(
        site_publication.system_store,
        "list_languages",
        lambda: [
            {"code": "en-US", "name": "English", "flag": "🇺🇸"},
            {"code": "de-DE", "name": "Deutsch", "flag": "🇩🇪"},
        ],
    )
    monkeypatch.setattr(
        site_publication.system_store,
        "get_language",
        lambda code: {
            "code": code,
            "name": code,
            "flag": "🌐",
            "dictionary": (
                dict(site_publication.EN_US)
                if code == "en-US"
                else {"site.runtime.search": "Suchen"}
            ),
        },
    )

    with pytest.raises(ValueError, match="missing .* required static-site translations"):
        site_publication.build_site_bundle(
            store_name="derrida-primary",
            works=["Glas"],
            title="Incomplete translation",
            locale="de-DE",
            languages=["de-DE"],
        )


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
    decoded_vectors = _chunk_vectors(chunks[0], 2)
    assert decoded_vectors[0] == pytest.approx([1.0, 0.0])
    assert decoded_vectors[1] == pytest.approx([0.0, 1.0])
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


def test_local_single_file_export_is_self_contained_and_allows_selected_model_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {
                "name": store_name,
                "embedding_model": "bge-m3:latest",
                "embedding_dimension": 3,
                "distance_metric": "cosine",
            },
            "records": [
                {"record": _record("r1", "Glas"), "embedding": [0.1, 0.2, 0.3]},
            ],
        },
    )

    bundle = site_publication.build_local_site_file(
        store_name="derrida-primary",
        works=["Glas"],
        title="Local Derrida",
    )

    html = bundle.payload.decode("utf-8")
    assert bundle.filename == "local-derrida.html"
    assert "<script src=" not in html
    assert "globalThis.__DERRIDAI_SITE_PACKAGE__=" in html
    assert "createClient" in html
    assert "__DERRIDAI_HOST_CAPABILITIES__" in html
    assert "connect-src http: https:" in html
    assert "script-src 'unsafe-inline'" in html


def test_nginx_export_contains_one_container_deployment_and_executable_scripts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {
                "name": store_name,
                "embedding_model": "bge-m3:latest",
                "embedding_dimension": 3,
                "distance_metric": "cosine",
            },
            "records": [
                {"record": _record("r1", "Glas"), "embedding": [0.1, 0.2, 0.3]},
            ],
        },
    )

    bundle = site_publication.build_nginx_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Served Derrida",
    )

    assert bundle.filename == "served-derrida-nginx.zip"
    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        assert archive.namelist() == [
            "index.html",
            "derridai-site.js",
            "Dockerfile",
            "nginx.conf",
            "start.sh",
            "stop.sh",
            "README.txt",
        ]
        dockerfile = archive.read("Dockerfile").decode("utf-8")
        nginx = archive.read("nginx.conf").decode("utf-8")
        start = archive.read("start.sh").decode("utf-8")
        stop = archive.read("stop.sh").decode("utf-8")
        start_mode = archive.getinfo("start.sh").external_attr >> 16
        stop_mode = archive.getinfo("stop.sh").external_attr >> 16

    assert dockerfile.startswith("# Generated by DerridAI")
    assert "FROM nginx:1.27-alpine" in dockerfile
    assert "node" not in dockerfile.casefold()
    assert "python" not in dockerfile.casefold()
    assert "proxy_pass" not in nginx
    assert "location = /healthz" in nginx
    assert start.count("docker run") == 1
    assert "docker compose" not in start.casefold()
    assert "docker rm -f" in stop
    assert start_mode & 0o111
    assert stop_mode & 0o111


def test_every_translation_key_used_by_the_site_runtime_exists_in_both_locales() -> None:
    import re
    from pathlib import Path

    from app.locales.en_us import EN_US
    from app.locales.fr_ca import FR_CA

    source = (Path(site_publication.__file__).parent / "site_assets" / "derridai-site.js").read_text("utf-8")
    used = set(re.findall(r"site\.runtime\.[a-z_0-9]+", source))
    assert used
    assert sorted(used - set(EN_US)) == []
    assert sorted(used - set(FR_CA)) == []

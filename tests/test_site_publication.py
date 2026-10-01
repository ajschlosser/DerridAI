# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import base64
import gzip
import io
import json
import struct
import zipfile

import pytest
from app import site_publication
from app.chroma_store import ChromaStore
from app.site_publication import TRANSFORMERS_GLOBAL


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

    assert publication["format"] == "derridai-static-site-v5"
    assert publication["corpus_id"] == "derrida-primary"
    assert [work["work"] for work in publication["works"]] == ["Glas", "Rogues"]
    assert publication["features"]["browser_llm"] is False
    assert publication["features"]["derridai_sdk"] is True
    assert publication["features"]["host_supplied_generation"] is True
    assert publication["features"]["browser_providers"] is True
    assert publication["features"]["browser_vector_index"] is True
    assert publication["features"]["transformers_runtime"] == "inline"
    assert "direct_provider_endpoints" not in publication["features"]
    assert publication["features"]["progressive_work_loading"] is True
    assert publication["vector_index"]["dimension"] == 3
    assert publication["vector_index"]["model"] == "bge-m3:latest"
    # Providers are configured by the reader in the browser; nothing about them is exported.
    assert "provider_profiles" not in publication
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
    assert "site.runtime.discover_models" in site_runtime
    assert "derridai.site.providers." in site_runtime
    assert "site.runtime.save_provider" in site_runtime
    assert "site.runtime.provider_local_help" in site_runtime
    # The shared browser client contains provider adapters but no provider profile, endpoint, or credential.
    assert "https://models.example" not in site_runtime
    assert "MUST-NOT-EXPORT" not in site_runtime
    assert f"globalThis.{TRANSFORMERS_GLOBAL}=" in site_runtime
    assert "wasm-unsafe-eval" in index_html
    assert bundle.record_count == 2
    assert bundle.work_count == 2


def test_site_bundle_can_omit_vectors_and_preserve_source_embedding_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        site_publication.store,
        "export_site_projection",
        lambda store_name, works: {
            "store": {
                "name": store_name,
                "embedding_provider": "ollama",
                "embedding_model": "bge-m3:latest",
                "embedding_dimension": 3,
                "distance_metric": "cosine",
                "text_field": "text",
            },
            "records": [
                {"record": _record("r1", "Glas"), "embedding": [0.1, 0.2, 0.3]},
            ],
        },
    )

    bundle = site_publication.build_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Browser-indexed Derrida",
        include_vectors=False,
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        package = _package_from_runtime(archive.read("derridai-site.js").decode("utf-8"))

    manifest = package["manifest"]
    chunk = package["chunks"][0]
    assert bundle.include_vectors is False
    assert manifest["features"]["semantic_search"] is False
    assert manifest["features"]["semantic_record_count"] == 0
    assert manifest["features"]["publication_vectors_included"] is False
    assert manifest["vector_index"]["model"] == "bge-m3:latest"
    assert manifest["vector_index"]["dimension"] is None
    assert manifest["source_collection"]["embedding_model"] == "bge-m3:latest"
    assert manifest["source_collection"]["embedding_dimension"] == 3
    assert _chunk_records(chunk)[0]["record_id"] == "r1"
    assert chunk["vector_ids"] == []
    assert chunk["vectors_b64"] == ""


def test_site_bundle_exports_only_selected_installed_languages_and_no_provider_profiles(
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
    bundle = site_publication.build_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Multilingual site",
        locale="de-DE",
        languages=["de-DE", "fr-CA"],
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
    assert "provider_profiles" not in manifest
    assert "direct_provider_endpoints" not in manifest["features"]


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
            "vendor/transformers/transformers.min.js",
            "vendor/transformers/ort-wasm-simd-threaded.mjs",
            "vendor/transformers/ort-wasm-simd-threaded.wasm",
            "vendor/transformers/NOTICE.txt",
            "vendor/transformers/LICENSE-transformers.js.txt",
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
    used = set(re.findall(r"""t\(["'](site\.runtime\.[a-z_0-9]+)["']""", source))
    tour_start = source.index("const TOUR_STEPS")
    tour_end = source.index("];", tour_start)
    tour_ids = re.findall(r"""\bid:\s*["']([a-z_0-9]+)["']""", source[tour_start:tour_end])
    used.update(
        f"site.runtime.tutorial_{step_id}_{suffix}"
        for step_id in tour_ids
        for suffix in ("title", "body")
    )
    assert used
    for role in ("embedding", "generation"):
        used |= {
            f"site.runtime.provider_{role}_{part}"
            for part in ("heading", "help", "select", "none", "none_help")
        }
    assert sorted(used - set(EN_US)) == []
    assert sorted(used - set(FR_CA)) == []


def _stub_projection(monkeypatch: pytest.MonkeyPatch) -> None:
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
            "records": [{"record": _record("r1", "Glas"), "embedding": [0.1, 0.2, 0.3]}],
        },
    )


_FAKE_RUNTIME = {
    "engine": b"export const engine = 1;",
    "license": b"Apache License fixture",
    "wasm_factory": b"export default function factory() {}",
    "wasm": b"\x00asm" + bytes(range(64)) * 4,
}


@pytest.fixture(autouse=True)
def _runtime_without_network(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Exports must never reach the network in tests; the cache module has its own tests."""
    calls: list[int] = []

    def fake_ensure_runtime() -> dict[str, bytes]:
        calls.append(1)
        return dict(_FAKE_RUNTIME)

    monkeypatch.setattr(site_publication, "ensure_runtime", fake_ensure_runtime)
    return calls


def test_two_file_site_embeds_the_transformers_runtime_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_projection(monkeypatch)
    bundle = site_publication.build_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="With runtime",
        include_transformers=True,
    )
    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        assert archive.namelist() == ["index.html", "derridai-site.js"]
        index_html = archive.read("index.html").decode("utf-8")
        runtime = archive.read("derridai-site.js").decode("utf-8")

    manifest = _package_from_runtime(runtime)["manifest"]
    assert manifest["features"]["transformers_runtime"] == "inline"
    assert manifest["features"]["transformers_local_models"] is None
    payload = json.loads(
        runtime.split(f"globalThis.{TRANSFORMERS_GLOBAL}=", 1)[1].split(";\n", 1)[0]
    )
    assert base64.b64decode(payload["engine_b64"]) == _FAKE_RUNTIME["engine"]
    assert base64.b64decode(payload["wasm_factory_b64"]) == _FAKE_RUNTIME["wasm_factory"]
    assert gzip.decompress(base64.b64decode(payload["wasm_gzip_b64"])) == _FAKE_RUNTIME["wasm"]
    assert "Apache License fixture" in payload["notice"]
    # WebAssembly and blob: modules are allowed only because the runtime is included.
    assert "'wasm-unsafe-eval'" in index_html
    assert "blob:" in index_html


def test_single_file_site_embeds_the_runtime_with_a_matching_standalone_csp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_projection(monkeypatch)
    bundle = site_publication.build_local_site_file(
        store_name="derrida-primary",
        works=["Glas"],
        title="With runtime",
        include_transformers=True,
    )
    html = bundle.payload.decode("utf-8")
    assert html.count(f"globalThis.{TRANSFORMERS_GLOBAL}=") == 1
    assert "<script src=" not in html
    assert "script-src 'unsafe-inline' 'wasm-unsafe-eval' blob:" in html
    assert "default-src 'none'" in html


def test_nginx_export_serves_the_runtime_as_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_projection(monkeypatch)
    bundle = site_publication.build_nginx_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Served",
        include_transformers=True,
    )
    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        names = set(archive.namelist())
        runtime_script = archive.read("derridai-site.js").decode("utf-8")
        dockerfile = archive.read("Dockerfile").decode("utf-8")
        nginx = archive.read("nginx.conf").decode("utf-8")
        start = archive.read("start.sh").decode("utf-8")
        wasm = archive.read("vendor/transformers/ort-wasm-simd-threaded.wasm")
        engine = archive.read("vendor/transformers/transformers.min.js")

    assert {
        "vendor/transformers/transformers.min.js",
        "vendor/transformers/ort-wasm-simd-threaded.mjs",
        "vendor/transformers/ort-wasm-simd-threaded.wasm",
        "vendor/transformers/NOTICE.txt",
    } <= names
    assert not any(name.startswith("models/") for name in names)
    assert engine == _FAKE_RUNTIME["engine"]
    assert wasm == _FAKE_RUNTIME["wasm"]
    # The deployment serves the runtime, so it is not duplicated inside the site script.
    assert f"globalThis.{TRANSFORMERS_GLOBAL}=" not in runtime_script
    manifest = _package_from_runtime(runtime_script)["manifest"]
    assert manifest["features"]["transformers_runtime"] == "files"
    assert manifest["features"]["transformers_local_models"] is None
    assert "COPY vendor /usr/share/nginx/html/vendor" in dockerfile
    assert "location /vendor/" in nginx
    assert "location /models/" not in nginx
    assert "/usr/share/nginx/html/models:ro" not in start


def test_nginx_provider_proxy_is_same_origin_streaming_safe_and_reaches_host_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_projection(monkeypatch)
    bundle = site_publication.build_nginx_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Proxied",
        provider_proxy_upstream="http://localhost:11434/v1",
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        nginx = archive.read("nginx.conf").decode("utf-8")
        start = archive.read("start.sh").decode("utf-8")
        readme = archive.read("README.txt").decode("utf-8")

    assert "location = /provider" in nginx
    assert "location /provider/" in nginx
    assert "limit_except GET POST" in nginx
    assert "proxy_pass http://host.docker.internal:11434/v1/;" in nginx
    assert "proxy_buffering off;" in nginx
    assert "proxy_read_timeout 300s;" in nginx
    assert "--add-host=host.docker.internal:host-gateway" in start
    assert "Browser endpoint base: /provider" in readme
    assert "provider-side browser CORS settings" in readme
    assert "SECURITY:" in readme


def test_nginx_provider_proxy_remote_upstream_does_not_require_host_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_projection(monkeypatch)
    bundle = site_publication.build_nginx_site_bundle(
        store_name="derrida-primary",
        works=["Glas"],
        title="Remote proxy",
        provider_proxy_upstream="https://models.example.test/v1",
    )
    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        nginx = archive.read("nginx.conf").decode("utf-8")
        start = archive.read("start.sh").decode("utf-8")

    assert "proxy_pass https://models.example.test/v1/;" in nginx
    assert "--add-host=host.docker.internal:host-gateway" not in start


@pytest.mark.parametrize(
    "upstream",
    [
        "ftp://localhost:11434/v1",
        "http://user:secret@localhost:11434/v1",
        "http://localhost:11434/v1?debug=1",
        "http://localhost:11434/v1#fragment",
        "http://localhost:11434/v1;include",
    ],
)
def test_nginx_provider_proxy_rejects_unsafe_upstreams(upstream: str) -> None:
    with pytest.raises(ValueError, match="Provider proxy upstream"):
        site_publication._normalize_provider_proxy_upstream(upstream)


def test_every_export_fetches_the_runtime(
    monkeypatch: pytest.MonkeyPatch, _runtime_without_network: list[int]
) -> None:
    _stub_projection(monkeypatch)
    site_publication.build_site_bundle(store_name="derrida-primary", works=["Glas"], title="Plain")
    site_publication.build_nginx_site_bundle(store_name="derrida-primary", works=["Glas"], title="Plain")
    assert _runtime_without_network


def test_export_fails_before_corpus_work_when_the_runtime_cannot_be_downloaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.site_runtime_cache import RuntimeUnavailableError

    def unavailable() -> dict[str, bytes]:
        raise RuntimeUnavailableError("offline")

    def projection_must_not_run(*_args: object) -> dict:
        raise AssertionError("corpus work started before the runtime was available")

    monkeypatch.setattr(site_publication, "ensure_runtime", unavailable)
    monkeypatch.setattr(site_publication.store, "export_site_projection", projection_must_not_run)
    with pytest.raises(RuntimeUnavailableError):
        site_publication.build_site_bundle(
            store_name="derrida-primary", works=["Glas"], title="X", include_transformers=True
        )


def test_export_requests_ignore_legacy_provider_profile_ids() -> None:
    from app.routers.sites import SiteExportRequest

    request = SiteExportRequest(
        store="derrida-primary", works=["Glas"], provider_profile_ids=["openai-main"]
    )
    assert not hasattr(request, "provider_profile_ids")
    assert request.include_transformers is True

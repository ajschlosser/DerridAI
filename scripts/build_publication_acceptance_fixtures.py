# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import argparse
import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_storage_root = Path(tempfile.mkdtemp(prefix="derridai-publication-acceptance-"))
atexit.register(shutil.rmtree, _storage_root, ignore_errors=True)
os.environ.setdefault("CHROMA_DATA_ROOT", str(_storage_root))
os.environ.setdefault("CHROMA_PATH", str(_storage_root / "chroma"))
os.environ.setdefault("AUTH_DB_PATH", str(_storage_root / ".home" / "derridai-auth.sqlite3"))
os.environ.setdefault("SYSTEM_DB_PATH", str(_storage_root / ".home" / "derridai-system.sqlite3"))
sys.path.insert(0, str(ROOT / "api"))

from app import site_publication  # noqa: E402


def _record() -> dict:
    return {
        "record_id": "acceptance-r1",
        "source_document_id": "acceptance-source",
        "source_spans": [
            {
                "source_document_id": "acceptance-source",
                "source_unit_id": "acceptance-unit-r1",
                "printed_page": "12",
            }
        ],
        "work": "Glas",
        "document_author": "Jacques Derrida",
        "citation": "Derrida, Jacques. Glas.",
        "speaker": "Derrida",
        "position_holder": "Derrida",
        "stance": "argues",
        "discourse_role": "analysis",
        "text": "Hospitality exceeds the economy of conditional exchange.",
    }


def _install_fixture_sources() -> None:
    site_publication.store.export_site_projection = lambda store_name, works: {
        "store": {
            "name": store_name,
            "embedding_model": "bge-m3:latest",
            "embedding_dimension": 2,
            "distance_metric": "cosine",
            "text_field": "text",
            "filter_fields": ["work", "speaker"],
        },
        "records": [{"record": _record(), "embedding": [1.0, 0.0]}],
    }
    site_publication.system_store.list_languages = lambda: [
        {"code": "en-US", "name": "English", "flag": "🇺🇸"}
    ]
    site_publication.system_store.get_language = lambda code: {
        "code": code,
        "name": "English",
        "flag": "🇺🇸",
        "dictionary": dict(site_publication.EN_US),
    }
    site_publication.system_store.researcher_profiles = lambda: []


def build(output_dir: Path) -> None:
    _install_fixture_sources()
    output_dir.mkdir(parents=True, exist_ok=True)

    local = site_publication.build_local_site_file(
        store_name="acceptance-corpus",
        works=["Glas"],
        title="DerridAI publication acceptance",
        description="Generated acceptance fixture.",
        locale="en-US",
        languages=["en-US"],
        provider_profile_ids=[],
    )
    (output_dir / "local.html").write_bytes(local.payload)

    nginx = site_publication.build_nginx_site_bundle(
        store_name="acceptance-corpus",
        works=["Glas"],
        title="DerridAI publication acceptance",
        description="Generated acceptance fixture.",
        locale="en-US",
        languages=["en-US"],
        provider_profile_ids=[],
    )
    (output_dir / "nginx.zip").write_bytes(nginx.payload)

    print(output_dir / "local.html")
    print(output_dir / "nginx.zip")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    build(args.output_dir)


if __name__ == "__main__":
    main()

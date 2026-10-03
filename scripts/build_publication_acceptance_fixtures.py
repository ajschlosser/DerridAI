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


def _provider_profiles() -> list[dict]:
    return [
        {
            "id": "acceptance-provider",
            "name": "Acceptance provider",
            "type": "openai",
            "base_url": "https://models.example.test/v1",
            "model": "fixture-generation",
            "has_api_key": False,
        }
    ]


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
    site_publication.system_store.researcher_profiles = _provider_profiles


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
    )
    (output_dir / "local.html").write_bytes(local.payload)

    local_provider = site_publication.build_local_site_file(
        store_name="acceptance-corpus",
        works=["Glas"],
        title="DerridAI provider acceptance",
        description="Generated direct-provider acceptance fixture.",
        locale="en-US",
        languages=["en-US"],
    )
    (output_dir / "local-provider.html").write_bytes(local_provider.payload)

    nginx = site_publication.build_nginx_site_bundle(
        store_name="acceptance-corpus",
        works=["Glas"],
        title="DerridAI publication acceptance",
        description="Generated acceptance fixture.",
        locale="en-US",
        languages=["en-US"],
        provider_proxy_upstream="http://localhost:11434/v1",
    )
    (output_dir / "nginx.zip").write_bytes(nginx.payload)

    print(output_dir / "local.html")
    print(output_dir / "local-provider.html")
    print(output_dir / "nginx.zip")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    build(args.output_dir)


if __name__ == "__main__":
    main()

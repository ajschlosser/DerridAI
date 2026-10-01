# Copyright 2026 Aaron John Schlosser, PhD.
"""Generate real static-site artifacts for browser/container acceptance tests."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import site_publication  # noqa: E402


def _record() -> dict:
    return {
        "record_id": "acceptance-r1",
        "record_revision": "1",
        "source_document_id": "acceptance-source",
        "source_spans": [
            {
                "source_document_id": "acceptance-source",
                "source_unit_id": "acceptance-unit-1",
                "printed_page": "12",
            }
        ],
        "work": "Glas",
        "document_author": "Jacques Derrida",
        "citation": "Derrida, Jacques. Glas. p. 12.",
        "speaker": "Derrida",
        "position_holder": "Derrida",
        "stance": "argues",
        "discourse_role": "analysis",
        "text": "Hospitality exceeds conditional exchange in this acceptance fixture.",
    }


def _projection(store_name: str, _works: list[str]) -> dict:
    return {
        "store": {
            "name": store_name,
            "embedding_provider": "fixture",
            "embedding_model": "fixture-embedding",
            "embedding_dimension": 2,
            "embedding_revision": "1",
            "distance_metric": "cosine",
            "text_field": "text",
            "filter_fields": ["work", "speaker"],
        },
        "records": [{"record": _record(), "embedding": [1.0, 0.0]}],
    }


def _language(code: str) -> dict:
    if code != "en-US":
        raise AssertionError(f"Unexpected acceptance language: {code}")
    return {
        "code": code,
        "name": "English",
        "flag": "EN",
        "dictionary": dict(site_publication.EN_US),
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


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (
        patch.object(site_publication.store, "export_site_projection", side_effect=_projection),
        patch.object(
            site_publication.system_store,
            "list_languages",
            return_value=[{"code": "en-US", "name": "English", "flag": "EN"}],
        ),
        patch.object(site_publication.system_store, "get_language", side_effect=_language),
        patch.object(
            site_publication.system_store,
            "researcher_profiles",
            side_effect=_provider_profiles,
        ),
    ):
        local = site_publication.build_local_site_file(
            store_name="acceptance-corpus",
            works=["Glas"],
            title="DerridAI Publication Acceptance",
            description="Generated acceptance fixture.",
            locale="en-US",
            languages=["en-US"],
        )
        nginx = site_publication.build_nginx_site_bundle(
            store_name="acceptance-corpus",
            works=["Glas"],
            title="DerridAI Publication Acceptance",
            description="Generated acceptance fixture.",
            locale="en-US",
            languages=["en-US"],
        )
        local_provider = site_publication.build_local_site_file(
            store_name="acceptance-corpus",
            works=["Glas"],
            title="DerridAI Provider Acceptance",
            description="Generated direct-provider acceptance fixture.",
            locale="en-US",
            languages=["en-US"],
            provider_profile_ids=["acceptance-provider"],
        )

    local_path = output_dir / "local.html"
    local_path.write_bytes(local.payload)
    local_provider_path = output_dir / "local-provider.html"
    local_provider_path.write_bytes(local_provider.payload)

    nginx_zip = output_dir / "nginx.zip"
    nginx_zip.write_bytes(nginx.payload)
    nginx_dir = output_dir / "nginx"
    nginx_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(nginx_zip) as archive:
        archive.extractall(nginx_dir)
        for script_name in ("start.sh", "stop.sh"):
            info = archive.getinfo(script_name)
            mode = (info.external_attr >> 16) & 0o777
            (nginx_dir / script_name).chmod(mode or 0o755)

    metadata = {
        "local": str(local_path),
        "local_provider": str(local_provider_path),
        "nginx": str(nginx_dir),
        "publication_id": local.publication_id,
        "record_count": local.record_count,
        "work_count": local.work_count,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    generate(args.output_dir.resolve())


if __name__ == "__main__":
    main()

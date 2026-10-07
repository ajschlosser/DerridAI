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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Run one deterministic source-to-corpus fixture through a compiled CLI artifact.

The local HTTP server implements only the OpenAI-compatible endpoint used by the
fixture. It derives syntactically valid structured answers from the JSON Schema
the compiled binary sends, so CI exercises the real provider transport, pipeline
runtime, Corpus Builder, automatic settlement, and publication code without an
external model or network dependency.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import zstandard as zstd


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    return parser


def _resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    node: Any = root
    for raw in reference.removeprefix("#/").split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        node = node[key]
    return node


def _schema_value(
    schema: dict[str, Any],
    *,
    root: dict[str, Any],
    name: str = "",
) -> Any:
    if "$ref" in schema:
        return _schema_value(_resolve_ref(root, str(schema["$ref"])), root=root, name=name)

    variants = schema.get("anyOf") or schema.get("oneOf")
    if isinstance(variants, list) and variants:
        if name in {"region_type", "discourse_role"}:
            non_null = [
                item
                for item in variants
                if isinstance(item, dict) and item.get("type") != "null"
            ]
            if non_null:
                return _schema_value(non_null[0], root=root, name=name)
        if name == "primary_text":
            return True
        null_variant = next(
            (
                item
                for item in variants
                if isinstance(item, dict) and item.get("type") == "null"
            ),
            None,
        )
        if null_variant is not None:
            return None
        return _schema_value(variants[0], root=root, name=name)

    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        if name == "region_type" and "main_text" in enum:
            return "main_text"
        return enum[0]

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((item for item in schema_type if item != "null"), "null")

    if schema_type == "object" or isinstance(schema.get("properties"), dict):
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        return {
            key: _schema_value(properties[key], root=root, name=key)
            for key in required
            if key in properties
        }
    if schema_type == "array":
        return []
    if schema_type in {"number", "integer"}:
        return 1
    if schema_type == "boolean":
        return name == "primary_text"
    if schema_type == "string":
        if name == "reason":
            return "Deterministic compiled-binary fixture."
        return "fixture"
    return None


def _block_ids(prompt: str) -> list[str]:
    match = re.search(r"Current source block IDs:\s*(\[[^\n]*\])", prompt)
    if not match:
        return []
    try:
        values = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [str(value) for value in values if str(value)]


def _structured_answer(
    *,
    schema_name: str,
    schema: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    if schema_name == "derridai_document_manifest":
        return {
            "title": "Deterministic Native CLI Fixture",
            "document_author": "DerridAI Test Fixture",
            "language": "en",
            "document_type": "essay",
            "notes": "",
        }

    payload = _schema_value(schema, root=schema)
    if not isinstance(payload, dict):
        payload = {}

    metadata = payload.get("metadata")
    assessments = payload.get("field_assessments")
    if isinstance(metadata, dict):
        if "region_type" in metadata:
            metadata["region_type"] = "main_text"
        if "primary_text" in metadata:
            metadata["primary_text"] = True
        if "discourse_role" in metadata and metadata["discourse_role"] is None:
            # The enum-bearing non-null branch is selected from the schema above,
            # but retain a stable fallback for provider schemas that inline nullable enums.
            metadata["discourse_role"] = "commentary"

    if isinstance(metadata, dict) and isinstance(assessments, dict):
        for field, assessment in assessments.items():
            if not isinstance(assessment, dict):
                continue
            value = metadata.get(field)
            assessment["confidence"] = 1.0
            assessment["needs_review"] = False
            assessment["reason"] = "Deterministic compiled-binary fixture."
            assessment["outcome"] = (
                "no_supported_value"
                if value is None or value == "" or value == []
                else "supported_value"
            )
            if "assessed_value" in assessment:
                assessment["assessed_value"] = value

    evidence_ids = _block_ids(prompt)
    if isinstance(metadata, dict) and evidence_ids:
        payload["field_evidence"] = {
            field: {
                "block_ids": evidence_ids[:1],
                "confidence": 1.0,
                "reason": "Exact source block used by deterministic fixture.",
            }
            for field in ("region_type", "primary_text", "discourse_role")
            if metadata.get(field) not in (None, "", [])
        }

    return payload


class _ProviderHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = str(((body.get("messages") or [{}])[0]).get("content") or "")
        response_format = body.get("response_format") or {}

        schema_name = ""
        schema: dict[str, Any] = {}
        json_schema = response_format.get("json_schema")
        if isinstance(json_schema, dict):
            schema_name = str(json_schema.get("name") or "")
            raw_schema = json_schema.get("schema")
            if isinstance(raw_schema, dict):
                schema = raw_schema

        if schema:
            answer = _structured_answer(
                schema_name=schema_name,
                schema=schema,
                prompt=prompt,
            )
        else:
            # The bibliographic candidate selector uses JSON mode rather than a
            # strict schema. -1 preserves the deterministic source metadata.
            answer = {"candidate_index": -1}

        payload = json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": json.dumps(answer)},
                        "finish_reason": "stop",
                    }
                ]
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def main() -> int:
    args = _parser().parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binary = manifest_path.parent / str(manifest["artifact_path"])
    if not binary.is_file():
        raise FileNotFoundError(binary)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _ProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with tempfile.TemporaryDirectory(prefix="derridai-native-corpus-") as tmp:
            root = Path(tmp)
            source = root / "fixture.txt"
            source.write_text(
                "Responsibility cannot be reduced to a calculation of reciprocal exchange. "
                "The claim is presented here as the primary argument of this fixture.",
                encoding="utf-8",
            )
            output = root / "fixture.jsonl.zst"
            workspace = root / "workspace"
            config = root / "corpus-run.yaml"
            config.write_text(
                f"""version: 1
source:
  ocr_mode: never
  detect_page_numbers: false
processing:
  segmentation:
    mode: source_units
    source_units_per_record: 1
  text:
    clean: false
    llm_touchup: false
  document_intelligence:
    profile: none
    provider: auto
    include_events: false
metadata:
  schema_id: default
  document:
    title: Deterministic Native CLI Fixture
    document_author: DerridAI Test Fixture
enrichment:
  mode: fast
  semantic_indexing: false
  passes: 1
provider:
  type: openai
  model: deterministic-fixture
  base_url: http://127.0.0.1:{server.server_port}
  concurrency: 1
review:
  mode: automatic
  min_confidence: 0.5
  unresolved: best_guess
publication:
  profile: research
  compression: zstd
""",
                encoding="utf-8",
            )

            migrated = root / "corpus-run-v2.yaml"
            _run(
                [
                    str(binary),
                    "config",
                    "migrate",
                    "--config",
                    str(config),
                    "--output",
                    str(migrated),
                ]
            )
            validated = json.loads(
                _run(
                    [
                        str(binary),
                        "config",
                        "validate",
                        "--config",
                        str(migrated),
                        "--json",
                    ]
                ).stdout
            )
            if validated.get("version") != 2:
                raise RuntimeError("Compiled binary did not validate the migrated v2 run envelope.")

            result = json.loads(
                _run(
                    [
                        str(binary),
                        "corpus",
                        "build",
                        "--source",
                        str(source),
                        "--config",
                        str(migrated),
                        "--output",
                        str(output),
                        "--workspace",
                        str(workspace),
                        "--json",
                        "--quiet",
                    ]
                ).stdout
            )
            if result.get("status") != "ok":
                raise RuntimeError(f"Unexpected corpus result: {result!r}")
            if Path(str(result.get("output") or "")).resolve() != output.resolve():
                raise RuntimeError("Compiled corpus result reported an unexpected output path.")
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError("Compiled corpus build produced no research artifact.")

            with output.open("rb") as handle:
                reader = zstd.ZstdDecompressor().stream_reader(handle)
                raw = reader.read().decode("utf-8")
            records = [json.loads(line) for line in raw.splitlines() if line.strip()]
            if not records:
                raise RuntimeError("Compiled research publication contains no records.")
            if not any("Responsibility" in str(record.get("text") or "") for record in records):
                raise RuntimeError("Compiled publication did not preserve the fixture source text.")
            if any("api_key" in json.dumps(record) for record in records):
                raise RuntimeError("Compiled publication unexpectedly exposed provider credentials.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

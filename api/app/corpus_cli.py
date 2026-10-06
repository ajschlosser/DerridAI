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

"""Native/headless DerridAI command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from enum import IntEnum
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .config import APP_VERSION
from .corpus_cli_config import dump_processing_config_yaml, load_processing_config


class ExitCode(IntEnum):
    OK = 0
    USAGE_OR_CONFIG = 2
    UNSUPPORTED_SOURCE = 3
    MISSING_CAPABILITY = 4
    PIPELINE = 5
    PROVIDER = 6
    VALIDATION = 7
    OUTPUT_IO = 8
    CANCELLED = 130


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="derridai",
        description="Build and validate DerridAI scholarly corpora without the web application.",
    )
    parser.add_argument("--version", action="version", version=f"DerridAI {APP_VERSION}")

    commands = parser.add_subparsers(dest="command", required=True)

    config = commands.add_parser(
        "config",
        help="Validate and inspect processing configuration.",
    )
    config_commands = config.add_subparsers(dest="config_command", required=True)
    validate = config_commands.add_parser(
        "validate",
        help="Validate a corpus-processing YAML file.",
    )
    validate.add_argument("--config", required=True, type=Path)
    validate.add_argument(
        "--json",
        action="store_true",
        help="Write the validated, secret-free configuration as JSON.",
    )

    migrate = config_commands.add_parser(
        "migrate",
        help="Migrate legacy v1 YAML to the canonical v2 corpus-run envelope.",
    )
    migrate.add_argument("--config", required=True, type=Path)
    migrate.add_argument(
        "--output",
        type=Path,
        help="Write migrated YAML here instead of stdout.",
    )

    pipeline = commands.add_parser(
        "pipeline",
        help="Inspect the pipeline contract compiled into this DerridAI build.",
    )
    pipeline_commands = pipeline.add_subparsers(dest="pipeline_command", required=True)
    capabilities = pipeline_commands.add_parser(
        "capabilities",
        help="Report pipeline contract and strategy versions.",
    )
    capabilities.add_argument(
        "--json",
        action="store_true",
        help="Write the machine-readable pipeline capability identity.",
    )

    corpus = commands.add_parser(
        "corpus",
        help="Build scholarly corpus artifacts.",
    )
    corpus_commands = corpus.add_subparsers(dest="corpus_command", required=True)
    build = corpus_commands.add_parser(
        "build",
        help="Build one source into a research or cELF .jsonl.zst corpus.",
    )
    build.add_argument("--source", required=True, type=Path)
    build.add_argument("--config", required=True, type=Path)
    build.add_argument("--output", type=Path)
    build.add_argument(
        "--workspace",
        type=Path,
        help="Retain build state in this workspace instead of a generated user-data run.",
    )
    build.add_argument(
        "--celf",
        action="store_true",
        help="Override publication.profile and emit the cELF publication artifact.",
    )
    build.add_argument(
        "--json",
        action="store_true",
        help="Write only the final machine-readable run result to stdout.",
    )
    build.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable progress on stderr.",
    )

    return parser


def _validate_config(path: Path, *, as_json: bool) -> int:
    try:
        config = load_processing_config(path)
    except (ValueError, ValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    if as_json:
        print(json.dumps(config.public_snapshot(), ensure_ascii=False, sort_keys=True))
    else:
        print(f"Configuration is valid (version {config.version}).")
    return int(ExitCode.OK)


def _migrate_config(path: Path, *, output: Path | None) -> int:
    """Migrate one legacy v1 file without inventing pipeline identity."""

    try:
        config = load_processing_config(path)
    except (ValueError, ValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    if config.version != 1:
        print(
            "Configuration error: config migrate currently accepts v1 input only.",
            file=sys.stderr,
        )
        return int(ExitCode.USAGE_OR_CONFIG)

    from .corpus_run_config import migrate_v1_to_v2
    from .pipelines.defaults import built_in_assignment, built_in_pipeline

    try:
        assignment = built_in_assignment("corpus_metadata_enrichment")
        if assignment is None:
            raise ValueError(
                "This DerridAI build does not define a default corpus metadata enrichment pipeline."
            )
        pipeline = built_in_pipeline(
            assignment.pipeline_id,
            assignment.pipeline_version,
        )
        if pipeline is None:
            raise ValueError(
                "The default corpus metadata enrichment pipeline is unavailable."
            )
        migrated = migrate_v1_to_v2(config, pipeline=pipeline)
        rendered = dump_processing_config_yaml(migrated)
    except (KeyError, ValueError, ValidationError) as exc:
        print(f"Configuration migration failed: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    if output is None:
        sys.stdout.write(rendered)
        return int(ExitCode.OK)

    destination = output.expanduser().resolve()
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(destination)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        print(f"Configuration migration failed: {exc}", file=sys.stderr)
        return int(ExitCode.OUTPUT_IO)

    print(destination)
    return int(ExitCode.OK)


def _pipeline_capabilities(*, as_json: bool) -> int:
    """Report the exact pipeline compatibility surface compiled into this build."""

    from .pipelines.capabilities import pipeline_contract_identity

    payload = pipeline_contract_identity()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Pipeline contract "
            f"{payload['pipeline_contract_version']} "
            f"(DerridAI {payload['application_version']})"
        )
        print(
            "Minimum readable pipeline version: "
            f"{payload['minimum_readable_pipeline_version']}"
        )
        for strategy_id, strategy in payload["strategies"].items():
            print(f"{strategy_id} v{strategy['version']}")
    return int(ExitCode.OK)


def _progress_printer(build: dict[str, Any]) -> None:
    progress = max(0.0, min(1.0, float(build.get("progress") or 0.0)))
    stage = str(build.get("stage") or build.get("status") or "working")
    completed = build.get("metadata_completed")
    total = build.get("metadata_total")
    metadata = (
        f" · metadata {completed}/{total}"
        if completed is not None and total is not None
        else ""
    )
    print(f"[{progress * 100:5.1f}%] {stage}{metadata}", file=sys.stderr)


def _error_code(category: str) -> ExitCode:
    return {
        "source": ExitCode.UNSUPPORTED_SOURCE,
        "capability": ExitCode.MISSING_CAPABILITY,
        "pipeline": ExitCode.PIPELINE,
        "provider": ExitCode.PROVIDER,
        "validation": ExitCode.VALIDATION,
        "output": ExitCode.OUTPUT_IO,
    }.get(category, ExitCode.PIPELINE)


def _build_corpus(args: argparse.Namespace) -> int:
    try:
        config = load_processing_config(args.config)
        # Resolve required secret environment variables before reading/extracting
        # a potentially large source file.
        config.build_request()
    except (ValueError, ValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    from .headless_corpus_runner import HeadlessCorpusError, HeadlessCorpusRunner

    runner = HeadlessCorpusRunner(workspace=args.workspace)
    try:
        result = runner.run(
            args.source,
            config,
            output=args.output,
            force_profile="celf" if args.celf else None,
            progress=None if args.quiet else _progress_printer,
        )
    except KeyboardInterrupt:
        print("Corpus build cancelled.", file=sys.stderr)
        return int(ExitCode.CANCELLED)
    except HeadlessCorpusError as exc:
        print(f"Corpus build failed: {exc}", file=sys.stderr)
        return int(_error_code(exc.category))

    payload = result.as_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(result.output)
    return int(ExitCode.OK)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a stable process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)

    if args.command == "config" and args.config_command == "validate":
        return _validate_config(args.config, as_json=args.json)
    if args.command == "config" and args.config_command == "migrate":
        return _migrate_config(args.config, output=args.output)
    if args.command == "pipeline" and args.pipeline_command == "capabilities":
        return _pipeline_capabilities(as_json=args.json)
    if args.command == "corpus" and args.corpus_command == "build":
        return _build_corpus(args)

    parser.error("Unsupported command")
    return int(ExitCode.USAGE_OR_CONFIG)


if __name__ == "__main__":
    raise SystemExit(main())

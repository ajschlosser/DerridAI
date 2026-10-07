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
from .corpus_run_config import (
    HEADLESS_CORPUS_PIPELINE_FEATURES,
    CorpusRunConfigV2,
    dump_run_config,
    load_run_config,
    migrate_v1_config,
)


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
        help="Validate, inspect, and migrate corpus run configuration.",
    )
    config_commands = config.add_subparsers(dest="config_command", required=True)
    validate = config_commands.add_parser(
        "validate",
        help="Validate a v1 processing file or v2 corpus-run envelope.",
    )
    validate.add_argument("--config", required=True, type=Path)
    validate.add_argument(
        "--json",
        action="store_true",
        help="Write the validated, secret-free configuration as JSON.",
    )

    migrate = config_commands.add_parser(
        "migrate",
        help="Migrate legacy v1 processing YAML to the v2 pipeline-bound run envelope.",
    )
    migrate.add_argument("--config", required=True, type=Path)
    migrate.add_argument(
        "--output",
        type=Path,
        help="Write the migrated configuration here instead of stdout.",
    )
    migrate.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of YAML.",
    )

    pipeline = commands.add_parser(
        "pipeline",
        help="Inspect the pipeline contract compiled into this DerridAI executable.",
    )
    pipeline_commands = pipeline.add_subparsers(dest="pipeline_command", required=True)
    capabilities = pipeline_commands.add_parser(
        "capabilities",
        help="Report pipeline contract and strategy versions.",
    )
    capabilities.add_argument(
        "--json",
        action="store_true",
        help="Write machine-readable capability information.",
    )

    doctor = commands.add_parser(
        "doctor",
        help="Check headless pipeline compatibility before starting a corpus build.",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Write machine-readable diagnostics.",
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
        config = load_run_config(path)
    except (ValueError, ValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    if as_json:
        print(json.dumps(config.public_snapshot(), ensure_ascii=False, sort_keys=True))
    else:
        kind = (
            f"{config.format} v{config.version}"
            if isinstance(config, CorpusRunConfigV2)
            else f"legacy v{config.version}"
        )
        print(f"Configuration is valid ({kind}).")
    return int(ExitCode.OK)


def _migrate_config(
    path: Path,
    *,
    output: Path | None,
    as_json: bool,
) -> int:
    try:
        loaded = load_run_config(path)
        config = loaded if isinstance(loaded, CorpusRunConfigV2) else migrate_v1_config(loaded)
    except (ValueError, ValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    rendered = (
        json.dumps(
            config.public_snapshot(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
        if as_json
        else dump_run_config(config)
    )
    if output is None:
        sys.stdout.write(rendered)
        return int(ExitCode.OK)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"Output error: {exc}", file=sys.stderr)
        return int(ExitCode.OUTPUT_IO)
    print(str(output))
    return int(ExitCode.OK)


def _pipeline_capabilities(*, as_json: bool) -> int:
    from .pipelines.compatibility import pipeline_contract_identity

    payload = pipeline_contract_identity()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Pipeline contract "
            f"v{payload['pipeline_contract_version']} · DerridAI "
            f"{payload['application_version']} · "
            f"{len(payload['strategies'])} strategies"
        )
    return int(ExitCode.OK)


def _doctor(*, as_json: bool) -> int:
    from .pipelines.compatibility import pipeline_contract_identity
    from .pipelines.manager import pipeline_manager

    available: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for feature in HEADLESS_CORPUS_PIPELINE_FEATURES:
        try:
            resolved = pipeline_manager.resolve(feature)
        except KeyError:
            missing.append(feature)
            continue
        pipeline = resolved["pipeline"]
        available[feature] = {
            "pipeline_id": pipeline["pipeline_id"],
            "pipeline_version": pipeline["version"],
            "pipeline_hash": resolved.get("pipeline_hash"),
        }

    payload = {
        "status": "ok" if not missing else "missing_capability",
        "pipeline_compatibility": pipeline_contract_identity(),
        "headless_corpus_pipelines": available,
        "missing_features": missing,
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        if missing:
            print(
                "Headless corpus pipeline check failed: missing "
                + ", ".join(missing),
                file=sys.stderr,
            )
        else:
            print(
                f"Headless corpus pipeline check passed ({len(available)} features)."
            )
    return int(ExitCode.OK if not missing else ExitCode.MISSING_CAPABILITY)


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
        config = load_run_config(args.config)
        # Resolve required secret environment variables before reading/extracting
        # a potentially large source file.
        config.build_request()
    except (ValueError, ValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE_OR_CONFIG)

    if isinstance(config, CorpusRunConfigV2):
        try:
            config.assert_installed_pipeline_bindings()
        except ValueError as exc:
            print(f"Pipeline capability error: {exc}", file=sys.stderr)
            return int(ExitCode.MISSING_CAPABILITY)

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
        return _migrate_config(
            args.config,
            output=args.output,
            as_json=args.json,
        )
    if args.command == "pipeline" and args.pipeline_command == "capabilities":
        return _pipeline_capabilities(as_json=args.json)
    if args.command == "doctor":
        return _doctor(as_json=args.json)
    if args.command == "corpus" and args.corpus_command == "build":
        return _build_corpus(args)

    parser.error("Unsupported command")
    return int(ExitCode.USAGE_OR_CONFIG)


if __name__ == "__main__":
    raise SystemExit(main())

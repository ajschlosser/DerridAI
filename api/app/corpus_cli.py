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
from enum import IntEnum
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from .config import APP_VERSION
from .corpus_cli_config import load_processing_config


class ExitCode(IntEnum):
    OK = 0
    USAGE_OR_CONFIG = 2
    UNSUPPORTED_SOURCE = 3
    MISSING_CAPABILITY = 4
    PIPELINE = 5
    PROVIDER = 6
    VALIDATION = 7
    OUTPUT_IO = 8


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="derridai",
        description="Build and validate DerridAI scholarly corpora without the web application.",
    )
    parser.add_argument("--version", action="version", version=f"DerridAI {APP_VERSION}")

    commands = parser.add_subparsers(dest="command", required=True)

    config = commands.add_parser("config", help="Validate and inspect processing configuration.")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    validate = config_commands.add_parser("validate", help="Validate a corpus-processing YAML file.")
    validate.add_argument("--config", required=True, type=Path)
    validate.add_argument(
        "--json",
        action="store_true",
        help="Write the validated, secret-free configuration as JSON.",
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a stable process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)

    if args.command == "config" and args.config_command == "validate":
        return _validate_config(args.config, as_json=args.json)

    parser.error("Unsupported command")
    return int(ExitCode.USAGE_OR_CONFIG)


if __name__ == "__main__":
    raise SystemExit(main())

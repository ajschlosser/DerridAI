#!/usr/bin/env python3
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

"""Copyright-header helper invoked by DerridAI’s tracked pre-commit hook.

Install this file as .git/hooks/pre-commit (and make it executable), or keep it
under a tracked hooks directory and point core.hooksPath there.

The hook only edits staged files. To avoid accidentally staging unrelated work,
it refuses to modify a file that also has unstaged changes.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HEADER_LINES = (
    "This file is part of DerridAI, a cELF-compliant research workspace",
    "Copyright © 2026  Aaron John Schlosser, PhD",
    "",
    "This program is free software: you can redistribute it and/or modify",
    "it under the terms of the GNU Affero General Public License as",
    "published by the Free Software Foundation, either version 3 of the",
    "License, or (at your option) any later version.",
    "",
    "This program is distributed in the hope that it will be useful,",
    "but WITHOUT ANY WARRANTY; without even the implied warranty of",
    "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the",
    "GNU Affero General Public License for more details.",
    "",
    "You should have received a copy of the GNU Affero General Public License",
    "along with this program.  If not, see <https://www.gnu.org/licenses/>.",
)

PROJECT_HEADER_MARKERS = (
    "this file is part of derridai",
    "aaron john schlosser",
)

# Directories whose tracked contents should not be rewritten by this hook.
# Third-party or generated material may carry independent licensing obligations.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
}

# Files where inserting a full textual header would make the format invalid or
# materially change data rather than add a comment. They are reported but left
# untouched. Use REUSE/DEP5 or another sidecar mechanism if these also require
# per-file licensing metadata.
COMMENTLESS_EXTENSIONS = {
    ".json",
    ".jsonl",
    ".ndjson",
    ".ipynb",
    ".csv",
    ".tsv",
    ".txt",
    ".lock",
}

COMMENTLESS_BASENAMES = {
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",  # generated; do not rewrite
    "poetry.lock",
    "uv.lock",
    "composer.lock",
    "cargo.lock",
    "license",
    "license.txt",
    "copying",
    "copying.txt",
    ".prettierrc",  # this repository uses JSON syntax for Prettier config
}


@dataclass(frozen=True)
class Style:
    kind: str
    prefix: str = ""
    open: str = ""
    close: str = ""
    middle: str = ""


HASH = Style("line", prefix="# ")
SLASH = Style("line", prefix="// ")
DASH = Style("line", prefix="-- ")
SEMICOLON = Style("line", prefix="; ")
REM = Style("line", prefix="REM ")
C_BLOCK = Style("block", open="/*", close=" */", middle=" * ")
HTML_BLOCK = Style("block", open="<!--", close="-->", middle="")
MDX_BLOCK = Style("block", open="{/*", close="*/}", middle=" * ")


EXTENSION_STYLES: dict[str, Style] = {
    # Hash comments
    ".py": HASH,
    ".pyi": HASH,
    ".pyx": HASH,
    ".sh": HASH,
    ".bash": HASH,
    ".zsh": HASH,
    ".fish": HASH,
    ".rb": HASH,
    ".r": HASH,
    ".pl": HASH,
    ".pm": HASH,
    ".t": HASH,
    ".yaml": HASH,
    ".yml": HASH,
    ".toml": HASH,
    ".ini": HASH,
    ".cfg": HASH,
    ".conf": HASH,
    ".properties": HASH,
    ".graphql": HASH,
    ".gql": HASH,
    ".dockerfile": HASH,
    # Slash comments
    ".js": C_BLOCK,
    ".jsx": C_BLOCK,
    ".ts": C_BLOCK,
    ".tsx": C_BLOCK,
    ".mjs": C_BLOCK,
    ".snap": C_BLOCK,  # Vitest/Jest snapshots are JavaScript modules.
    ".cjs": C_BLOCK,
    ".java": C_BLOCK,
    ".kt": C_BLOCK,
    ".kts": C_BLOCK,
    ".c": C_BLOCK,
    ".h": C_BLOCK,
    ".cc": C_BLOCK,
    ".cpp": C_BLOCK,
    ".cxx": C_BLOCK,
    ".hpp": C_BLOCK,
    ".hh": C_BLOCK,
    ".hxx": C_BLOCK,
    ".cs": C_BLOCK,
    ".go": SLASH,
    ".rs": C_BLOCK,
    ".swift": C_BLOCK,
    ".scala": C_BLOCK,
    ".groovy": C_BLOCK,
    ".gradle": C_BLOCK,
    ".proto": C_BLOCK,
    ".css": C_BLOCK,
    ".scss": C_BLOCK,
    ".sass": C_BLOCK,
    ".less": C_BLOCK,
    # SQL/Lua
    ".sql": DASH,
    ".lua": DASH,
    # Markup
    ".html": HTML_BLOCK,
    ".htm": HTML_BLOCK,
    ".xml": HTML_BLOCK,
    ".svg": HTML_BLOCK,
    ".vue": HTML_BLOCK,
    ".svelte": HTML_BLOCK,
    ".md": HTML_BLOCK,
    ".markdown": HTML_BLOCK,
    ".mdx": MDX_BLOCK,
    # Windows / PowerShell
    ".ps1": HASH,
    ".psm1": HASH,
    ".bat": REM,
    ".cmd": REM,
}

BASENAME_STYLES: dict[str, Style] = {
    "dockerfile": HASH,
    "makefile": HASH,
    "gnumakefile": HASH,
    "pre-commit": HASH,
    "pre-push": HASH,
    "requirements.txt": HASH,
    "constraints.txt": HASH,
    ".dockerignore": HASH,
    ".prettierignore": HASH,
    ".eslintignore": HASH,
    ".stylelintignore": HASH,
    ".npmignore": HASH,
    ".browserslistrc": HASH,
    ".npmrc": HASH,
    ".gitignore": HASH,
    ".gitattributes": HASH,
    ".editorconfig": HASH,
    ".gitkeep": HASH,
    ".env": HASH,
    ".pre-commit-config.yaml": HASH,
    ".pre-commit-config.yml": HASH,
}

CODING_RE = re.compile(r"coding[:=]\s*[-\w.]+")


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def nul_paths(output: bytes) -> list[str]:
    return [p.decode("utf-8", "surrogateescape") for p in output.split(b"\0") if p]


def staged_paths() -> list[str]:
    return nul_paths(
        run_git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR").stdout
    )


def tracked_paths() -> list[str]:
    return nul_paths(run_git("ls-files", "-z").stdout)


def unstaged_paths() -> set[str]:
    return set(nul_paths(run_git("diff", "--name-only", "-z").stdout))


def should_skip_path(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    # Playwright raw snapshot files are generated comparison data. Adding a
    # comment changes the snapshot value itself and makes the regression test
    # fail even though the rendered DOM is unchanged.
    if any(part.endswith("-snapshots") for part in path.parts):
        return True
    return False


def detect_style(path: Path) -> Style | None:
    name = path.name.lower()
    if name.startswith(".env"):
        return HASH
    if name.startswith("dockerfile."):
        return HASH
    if name in BASENAME_STYLES:
        return BASENAME_STYLES[name]
    return EXTENSION_STYLES.get(path.suffix.lower())


def is_commentless(path: Path) -> bool:
    name = path.name.lower()
    return name in COMMENTLESS_BASENAMES or path.suffix.lower() in COMMENTLESS_EXTENSIONS


def is_probably_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    try:
        data[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def dominant_newline(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf > lf else "\n"


def preamble_end(lines: list[str], path: Path) -> int:
    """Return line index after content that must remain first in the file."""
    i = 0
    suffix = path.suffix.lower()
    name = path.name.lower()

    if lines and lines[0].startswith("#!"):
        i = 1

    # Docker parser directives must remain before comments/instructions.
    # Preserve the standard syntax/escape directives before inserting a header.
    if path.name.lower().startswith("dockerfile"):
        while i < len(lines):
            stripped = lines[i].strip().lower()
            if stripped.startswith("# syntax=") or stripped.startswith("# escape="):
                i += 1
                continue
            break

    # PEP 263 encoding cookie must be on line 1 or 2.
    for j in range(i, min(i + 2, len(lines))):
        if CODING_RE.search(lines[j]):
            i = j + 1
            break

    # XML declaration must remain first.
    if i == 0 and lines and lines[0].lstrip("\ufeff").startswith("<?xml"):
        i = 1

    # Keep HTML doctype first.
    if suffix in {".html", ".htm"} and i == 0 and lines:
        if lines[0].lstrip().lower().startswith("<!doctype"):
            i = 1

    # CSS @charset must be the first non-BOM construct to be effective.
    if suffix in {".css", ".scss", ".sass", ".less"} and i == 0 and lines:
        if lines[0].lstrip("\ufeff").lower().startswith("@charset"):
            i = 1

    # PHP opening tag must precede comments written in PHP syntax. PHP itself is
    # intentionally unsupported below, but this makes future extension safer.
    if suffix == ".php" and i == 0 and lines and lines[0].lstrip().startswith("<?php"):
        i = 1

    # Markdown/MDX front matter must remain the first construct for many tools.
    if suffix in {".md", ".markdown", ".mdx"} and i == 0 and lines:
        first = lines[0].strip()
        if first in {"---", "+++"}:
            for j in range(1, min(len(lines), 500)):
                if lines[j].strip() == first:
                    i = j + 1
                    break

    # A dotenv-like file may be extensionless but still start with a shebang;
    # handled above. No additional preamble needed.
    _ = name
    return i


def strip_comment_syntax(block: str) -> str:
    cleaned: list[str] = []
    for raw in block.splitlines():
        s = raw.strip()
        for marker in ("<!--", "-->", "{/*", "*/}", "/*", "*/"):
            if s.startswith(marker):
                s = s[len(marker) :].lstrip()
            if s.endswith(marker):
                s = s[: -len(marker)].rstrip()
        if s.startswith("*"):
            s = s[1:].lstrip()
        for prefix in ("#", "//", "--", ";"):
            if s.startswith(prefix):
                s = s[len(prefix) :].lstrip()
                break
        if s.lower().startswith("rem "):
            s = s[4:].lstrip()
        cleaned.append(s)
    return "\n".join(cleaned).strip()


def leading_comment_block(lines: list[str], start: int) -> tuple[int, str] | None:
    """Return (end_line_exclusive, decommented_text) for a leading comment."""
    i = start
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return None

    stripped = lines[i].lstrip()

    block_pairs = (
        ("<!--", "-->"),
        ("{/*", "*/}"),
        ("/*", "*/"),
    )
    for opener, closer in block_pairs:
        if stripped.startswith(opener):
            j = i
            buf: list[str] = []
            while j < len(lines):
                buf.append(lines[j])
                if closer in lines[j]:
                    return j + 1, strip_comment_syntax("".join(buf))
                j += 1
            return None

    # Line-comment headers. Require a contiguous run of comment lines; blank
    # lines are part of the header only when themselves commented.
    prefixes = ("#", "//", "--", ";")
    matched_prefix: str | None = None
    for p in prefixes:
        if stripped.startswith(p):
            matched_prefix = p
            break
    if stripped.lower().startswith("rem "):
        matched_prefix = "REM"

    if matched_prefix is None:
        return None

    j = i
    buf = []
    while j < len(lines):
        s = lines[j].lstrip()
        if matched_prefix == "REM":
            if not s.lower().startswith("rem "):
                break
        elif not s.startswith(matched_prefix):
            break
        buf.append(lines[j])
        j += 1
    return j, strip_comment_syntax("".join(buf))


def classify_existing_header(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in PROJECT_HEADER_MARKERS):
        return "project"
    if "copyright" in lowered or "spdx-filecopyrighttext" in lowered:
        return "third-party"
    if "gnu affero general public license" in lowered and "derridai" in lowered:
        return "project"
    return "other"


def render_header(style: Style, newline: str) -> str:
    if style.kind == "line":
        out: list[str] = []
        bare_prefix = style.prefix.rstrip()
        for line in HEADER_LINES:
            if line:
                out.append(f"{style.prefix}{line}")
            else:
                out.append(bare_prefix)
        return newline.join(out) + newline + newline

    if style.kind == "block":
        out = [style.open]
        if style.middle:
            bare_middle = style.middle.rstrip()
            for line in HEADER_LINES:
                out.append(f"{style.middle}{line}" if line else bare_middle)
        else:
            out.extend(HEADER_LINES)
        out.append(style.close)
        return newline.join(out) + newline + newline

    raise AssertionError(f"Unknown comment style: {style.kind}")


def transform_text(text: str, path: Path, style: Style) -> tuple[str, bool]:
    newline = dominant_newline(text)
    # Work in LF internally, then restore the file's dominant newline convention.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    had_final_newline = normalized.endswith("\n")
    lines = normalized.splitlines(keepends=True)
    start = preamble_end(lines, path)

    existing = leading_comment_block(lines, start)
    remove_start = start
    remove_end = start

    if existing is not None:
        end, comment_text = existing
        kind = classify_existing_header(comment_text)
        if kind == "project":
            lowered_comment = comment_text.lower()
            if (
                "this file is part of derridai" in lowered_comment
                or "gnu affero general public license" in lowered_comment
            ):
                # A full DerridAI license header owns the complete leading
                # comment block emitted by this hook.
                remove_end = end
            else:
                # Legacy DerridAI headers were commonly one-line copyright
                # comments immediately followed by useful documentation
                # comments. Replace only the legacy copyright line; do not
                # consume adjacent comments that belong to the program.
                first = start
                while first < len(lines) and not lines[first].strip():
                    first += 1
                remove_end = min(first + 1, len(lines))

            # Remove blank lines following the old project header so insertion
            # remains exactly one blank line away from the file body.
            while remove_end < len(lines) and not lines[remove_end].strip():
                remove_end += 1
        elif kind == "third-party":
            raise RuntimeError(
                "leading third-party copyright/license notice detected; refusing to replace it"
            )

    header = render_header(style, "\n")
    body = "".join(lines[:remove_start]) + header + "".join(lines[remove_end:])

    # Preserve the original final-newline state for nonempty files. The inserted
    # header itself always ends cleanly; body data is otherwise left intact.
    if not had_final_newline and normalized and body.endswith("\n") and remove_end >= len(lines):
        body = body.rstrip("\n")

    if newline == "\r\n":
        body = body.replace("\n", "\r\n")

    return body, body != text


def stage(path: str) -> None:
    proc = run_git("add", "--", path, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "git add failed")


def main() -> int:
    try:
        run_git("rev-parse", "--git-dir")
    except subprocess.CalledProcessError:
        print("copyright hook: not inside a Git repository", file=sys.stderr)
        return 2

    all_mode = "--all" in sys.argv[1:]
    unknown_args = [arg for arg in sys.argv[1:] if arg != "--all"]
    if unknown_args:
        print(f"copyright hook: unknown argument(s): {' '.join(unknown_args)}", file=sys.stderr)
        print("usage: copyright_headers.py [--all]", file=sys.stderr)
        return 2

    candidates = tracked_paths() if all_mode else staged_paths()
    if not candidates:
        return 0

    unstaged = unstaged_paths()
    overlap = sorted(set(candidates) & unstaged)
    if overlap:
        print(
            "copyright hook: refusing to rewrite partially staged files because doing so "
            "could stage unrelated edits:",
            file=sys.stderr,
        )
        for path in overlap:
            print(f"  {path}", file=sys.stderr)
        print(
            "Stage the full file, stash the unstaged hunk, or commit it separately, then retry.",
            file=sys.stderr,
        )
        return 1

    changed: list[str] = []
    skipped_commentless: list[str] = []
    skipped_binary: list[str] = []
    unsupported: list[str] = []
    errors: list[str] = []

    for raw_path in candidates:
        path = Path(raw_path)

        if should_skip_path(path):
            continue
        if not path.exists() or path.is_dir() or path.is_symlink():
            continue

        try:
            data = path.read_bytes()
        except OSError as exc:
            errors.append(f"{raw_path}: {exc}")
            continue

        if is_probably_binary(data):
            skipped_binary.append(raw_path)
            continue

        style = detect_style(path)
        if style is None:
            if is_commentless(path):
                skipped_commentless.append(raw_path)
            else:
                unsupported.append(raw_path)
            continue

        bom = data.startswith(b"\xef\xbb\xbf")
        payload = data[3:] if bom else data
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            skipped_binary.append(raw_path)
            continue

        try:
            new_text, did_change = transform_text(text, path, style)
        except RuntimeError as exc:
            errors.append(f"{raw_path}: {exc}")
            continue

        if not did_change:
            continue

        new_data = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
        try:
            path.write_bytes(new_data)
            stage(raw_path)
        except (OSError, RuntimeError) as exc:
            errors.append(f"{raw_path}: {exc}")
            continue
        changed.append(raw_path)

    if changed:
        print(f"copyright hook: updated and staged {len(changed)} file(s):")
        for path in changed:
            print(f"  {path}")

    if skipped_commentless:
        print(
            "copyright hook: skipped commentless/data formats (a full header would invalidate or alter them):",
            file=sys.stderr,
        )
        for path in skipped_commentless:
            print(f"  {path}", file=sys.stderr)

    if skipped_binary:
        print(f"copyright hook: skipped {len(skipped_binary)} binary/non-UTF-8 file(s).", file=sys.stderr)

    if unsupported:
        print(
            "copyright hook: no safe comment syntax is configured for these staged text files:",
            file=sys.stderr,
        )
        for path in unsupported:
            print(f"  {path}", file=sys.stderr)
        print(
            "Add an extension/basename mapping or explicitly classify the format as commentless.",
            file=sys.stderr,
        )
        return 1

    if errors:
        print("copyright hook: errors:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

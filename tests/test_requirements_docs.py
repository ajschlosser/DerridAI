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

"""Product-requirements documentation contracts.

Why: docs/requirements is a normative traceability surface, not ordinary prose.
Broken test links, duplicate requirement IDs, stale matrix rows, or parent references
to missing global requirements would make the matrix misleading precisely when it is
needed for review and release work.

How: parse the checked-in Markdown using deliberately small structural rules. The
tests do not attempt to implement a general Markdown parser; they validate the link
and requirement-row conventions defined by docs/requirements/README.md.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ_DIR = ROOT / "docs" / "requirements"
INDEX = REQ_DIR / "README.md"
MATRIX = REQ_DIR / "TRACEABILITY_MATRIX.md"

REQUIREMENT_ROW = re.compile(r"^\|\s+\*\*(PRD-[A-Z0-9]+-\d+)\*\*\s+\|")
GLOBAL_ID = re.compile(r"PRD-G-\d+")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
TOTAL_REQUIREMENTS = re.compile(r"Total requirements: \*\*(\d+)\*\*")


def requirement_documents() -> list[Path]:
    """Return normative requirement documents, excluding index and derived matrix."""
    return sorted(
        path
        for path in REQ_DIR.glob("*.md")
        if path.name not in {"README.md", "TRACEABILITY_MATRIX.md"}
    )


def requirement_rows(path: Path) -> list[tuple[str, str]]:
    """Return requirement id and full table row for one normative document."""
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT_ROW.match(line)
        if match:
            rows.append((match.group(1), line))
    return rows


def test_requirements_index_links_every_normative_document() -> None:
    """The table of contents must link every normative requirements document once or more."""
    index = INDEX.read_text(encoding="utf-8")
    missing = [path.name for path in requirement_documents() if f"]({path.name})" not in index]
    assert missing == [], f"Requirements index is missing: {missing}"


def test_requirement_ids_are_unique_and_matrix_is_complete() -> None:
    """Stable requirement IDs must be unique, and the derived matrix must contain exactly that set."""
    by_id: dict[str, list[str]] = {}
    for path in requirement_documents():
        for requirement_id, _row in requirement_rows(path):
            by_id.setdefault(requirement_id, []).append(path.name)

    duplicates = {key: value for key, value in by_id.items() if len(value) > 1}
    assert duplicates == {}, f"Duplicate requirement IDs: {duplicates}"

    matrix_ids = {
        requirement_id
        for requirement_id, _row in requirement_rows(MATRIX)
    }
    expected = set(by_id)
    assert matrix_ids == expected, (
        "TRACEABILITY_MATRIX.md is stale. "
        f"Missing: {sorted(expected - matrix_ids)}; extra: {sorted(matrix_ids - expected)}"
    )

    match = TOTAL_REQUIREMENTS.search(MATRIX.read_text(encoding="utf-8"))
    assert match is not None, "TRACEABILITY_MATRIX.md must report its total requirement count"
    assert int(match.group(1)) == len(expected)


def test_requirement_parent_global_ids_exist() -> None:
    """Every referenced PRD-G parent must resolve to a defined global requirement."""
    global_path = REQ_DIR / "GLOBAL_REQUIREMENTS.md"
    globals_defined = {
        requirement_id
        for requirement_id, _row in requirement_rows(global_path)
        if requirement_id.startswith("PRD-G-")
    }
    broken: list[tuple[str, str, str]] = []
    for path in requirement_documents():
        for requirement_id, row in requirement_rows(path):
            for parent in GLOBAL_ID.findall(row):
                if parent not in globals_defined:
                    broken.append((path.name, requirement_id, parent))
    assert broken == [], f"Unknown global parent requirement(s): {broken}"


def test_requirement_rows_have_verification_content() -> None:
    """Every normative row must state how it is verified instead of leaving the last cell blank."""
    missing: list[tuple[str, str]] = []
    for path in requirement_documents():
        for requirement_id, row in requirement_rows(path):
            cells = [cell.strip() for cell in row.split("|")[1:-1]]
            if not cells or not cells[-1] or cells[-1] in {"-", "—"}:
                missing.append((path.name, requirement_id))
    assert missing == [], f"Requirements without verification content: {missing}"


def test_relative_markdown_links_resolve_inside_repository() -> None:
    """Relative Markdown links in the requirements corpus must resolve to checked-in files/directories."""
    broken: list[tuple[str, str]] = []
    escaped: list[tuple[str, str]] = []

    for path in sorted(REQ_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = raw_target.strip()
            if (
                not target
                or target.startswith("#")
                or target.startswith("http://")
                or target.startswith("https://")
                or target.startswith("mailto:")
            ):
                continue

            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                escaped.append((path.name, target))
                continue
            if not resolved.exists():
                broken.append((path.name, target))

    assert escaped == [], f"Requirements links escape repository root: {escaped}"
    assert broken == [], f"Broken relative requirements links: {broken}"

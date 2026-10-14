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

"""Locale scoping of RAG candidates must not drop records with no language."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.rag import _scope_rag_candidates  # noqa: E402


def _row(language):
    record = {"record_id": "r"}
    if language is not None:
        record["document_language"] = language
    return {"record": record}


def test_records_without_language_survive_locale_scope():
    rows = [_row(None), _row("fr"), _row("en")]
    kept = _scope_rag_candidates(rows, {"collection_role": "source"}, {"fr"})
    assert rows[0] in kept and rows[1] in kept and rows[2] not in kept

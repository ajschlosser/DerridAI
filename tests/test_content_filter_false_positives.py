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

"""Researcher content filter: avoid false positives on names and words.

Why: the filter blocks abusive language in researcher input, but this is a
philosophy corpus full of authors' names and archaic words; over-blocking would
make legitimate research impossible.
How: loads content_filter.py directly by file path (no app package import) and
calls contains_disallowed_language on sample strings.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_DUMMY_POLICY = {
    "status": "ready",
    "blocked_terms": [
        "zzblock",
        "qwvulgar",
        "aaarghword",
        "bbarghword",
        "ccarghword",
        "ddarghword",
        "eearghword",
        "ffarghword",
    ],
    "contextual_terms": [
        {"term": "widget", "allow_title_case": True, "allow_if_surrounding": [], "allow_if_before_markers": []},
        {"term": "flint", "allow_title_case": False, "allow_if_surrounding": ["pebble"], "allow_if_before_markers": []},
        {"term": "blot", "allow_title_case": False, "allow_if_surrounding": [], "allow_if_before_markers": ["word ", "term "]},
    ],
}


def _load_content_filter():
    """Import content_filter.py by path so the test needs no ChromaDB or FastAPI setup."""
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_bits", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_content_filter_avoids_name_and_substring_false_positives():
    """Names, look-alike words, and quoted mentions pass; real use and obfuscation are caught.

    Uses a dummy policy of placeholder words (no real terms in source). Contextual rules under test:
    title-case names are allowed ("Widget Higgins"), longer words containing a term are allowed ("Widgetry",
    "Flintstone"), a term is allowed next to a listed neighbor word ("flint" with "pebble"), and allowed
    after a marker like "the word" (mention, not use). The bare use ("you widget", "what the blot") and a
    dotted-out spelling ("z.z.b.l.o.c.k") are blocked.
    """
    content_filter = _load_content_filter()
    policies = [_DUMMY_POLICY]
    assert not content_filter.contains_disallowed_language("Widget Higgins discusses intermedia.", policies=policies)
    assert not content_filter.contains_disallowed_language("Widgetry and Flintstone are authors.", policies=policies)
    assert not content_filter.contains_disallowed_language("The technical term flint can mean pebble.", policies=policies)
    assert content_filter.contains_disallowed_language("you widget", policies=policies)
    assert content_filter.contains_disallowed_language("what the blot", policies=policies)
    assert not content_filter.contains_disallowed_language("the word blot", policies=policies)
    assert content_filter.contains_disallowed_language("z.z.b.l.o.c.k", policies=policies)

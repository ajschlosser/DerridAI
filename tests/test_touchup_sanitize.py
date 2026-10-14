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

import pytest
from app.corpus_builder import _sanitize_touchup_output as clean

SRC = "It was the best of times, it was the worst of times."


@pytest.mark.parametrize("proposed", [
    "<SOURCE_TEXT>It was the best of times, it was the worst of times.</SOURCE_TEXT>",
    "<SOURCE_TEXT/>It was the best of times, it was the worst of times.",
    "<SOURCE_TEXT>\nIt was the best of times, it was the worst of times.\n</SOURCE_TEXT>",
    "SOURCE_TEXT:\nIt was the best of times, it was the worst of times.",
    "<source_text> It was the best of times, it was the worst of times. </source_text>",
    "Corrected text: <SOURCE_TEXT/>\nIt was the best of times, it was the worst of times.\n<SOURCE_TEXT/>",
    "<output>It was the best of times, it was the worst of times.</output>",
    "---\nIt was the best of times,\nit was the worst of times.\n---",
])
def test_added_wrappers_are_removed(proposed):
    assert " ".join(clean(proposed, SRC).split()) == SRC


def test_markup_that_belongs_to_the_source_is_kept():
    src = "<b>Bold</b> statement, then more."
    assert clean("<b>Bold</b> statement, then more.", src) == src
    assert clean("<SOURCE_TEXT><b>Bold</b> statement, then more.</SOURCE_TEXT>", src) == src


def test_clean_output_is_left_alone():
    assert clean(SRC, SRC) == SRC
    assert clean("A line with < and > signs, 3 < 4.", "a line") == "A line with < and > signs, 3 < 4."


def test_identical_sanitized_output_is_detectable_as_no_change():
    proposed = clean("<SOURCE_TEXT>" + SRC + "</SOURCE_TEXT>", SRC)
    assert proposed == SRC

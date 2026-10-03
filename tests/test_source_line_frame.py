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

"""Text framed line-by-line with pipes still yields paragraphs and page numbers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.source_text import prose_to_blocks, strip_line_frame  # noqa: E402


def test_strip_line_frame_only_when_nearly_every_line_is_framed():
    framed = "| one\n| two\n| three\n| four"
    assert strip_line_frame(framed) == ("one\ntwo\nthree\nfour", "leading_pipe")
    plain = "one\ntwo | b\nthree\nfour"
    assert strip_line_frame(plain) == (plain, "")


def test_pipe_framed_source_keeps_paragraphs():
    text = "| First paragraph line.\n|\n| Second paragraph line.\n|\n| Third one."
    text = text.replace("|\n", "\n")
    info = {}
    blocks, _ = prose_to_blocks(text, extraction_method="test", detection_out=info)
    assert [b["text"] for b in blocks] == ["First paragraph line.", "Second paragraph line.", "Third one."]
    assert info["line_frame_stripped"] == "leading_pipe"

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

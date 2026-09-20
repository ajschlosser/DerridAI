import pytest
from app.corpus_metadata import _normalize_semantic_value
from app.metadata_values import clean, is_placeholder


@pytest.mark.parametrize("value", [
    "null", "None", " N/A ", "unknown", "Not specified", "-", "", "  ", "undefined",
    "The author of the current record", "the author", "This author", "the current author", "The speaker", "the narrator of this passage",
    "Unknown author", "author unknown", "an unnamed speaker", "The text", "the person", "The author of the text", "the reader",
])
def test_placeholders_and_generic_roles_are_not_values(value):
    assert is_placeholder(value) is True


@pytest.mark.parametrize("value", [
    "Jacques Derrida", "Emmanuel Levinas", "cities of refuge", "hospitality", "Anonymous", "The Author of Waverley", "Plato's Republic",
    "the concept of hospitality", "Authority", "Nullius in verba", "speaker of the house",
])
def test_real_values_are_kept(value):
    assert is_placeholder(value) is False


def test_lists_lose_only_their_placeholders():
    assert clean(["Derrida", "null", "the author", "Levinas"]) == ["Derrida", "Levinas"]
    assert clean("the author of the current record") is None and clean("Derrida") == "Derrida"


def test_a_model_proposal_of_a_placeholder_becomes_no_value_and_keeps_the_raw_text():
    assert _normalize_semantic_value("speaker", "The author of the current record") == (None, "The author of the current record")
    assert _normalize_semantic_value("persons", ["Derrida", "null"]) == (["Derrida"], ["Derrida", "null"])
    assert _normalize_semantic_value("speaker", "Derrida") == ("Derrida", None)

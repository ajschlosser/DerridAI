from app.error_severity import severity


def test_grades():
    assert severity("Author", "author.") == "cosmetic"
    assert severity("Jane Author", "Author") == "near_miss"
    assert severity("Author", "Husserl") == "substantive"
    assert severity("Author", None) == "cleared"
    assert severity(["a", "b"], "a, b") == "cosmetic"

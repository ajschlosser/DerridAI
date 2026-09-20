from app.error_severity import severity


def test_grades():
    assert severity("Derrida", "derrida.") == "cosmetic"
    assert severity("Jacques Derrida", "Derrida") == "near_miss"
    assert severity("Derrida", "Husserl") == "substantive"
    assert severity("Derrida", None) == "cleared"
    assert severity(["a", "b"], "a, b") == "cosmetic"

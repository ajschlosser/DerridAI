# Copyright 2026 Aaron John Schlosser, PhD.
"""Built-in language identity: a plain name and a stored flag, with no regional special cases.

Why: a language's name and flag are data stored with the language. Nothing should decide how a
flag looks from a locale code, and the interface must not carry regional variants or symbols of
its own. These tests keep that true.
How: reads the locale modules with `ast`, and drives SystemStore against a temporary database.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import system_store as store_module  # noqa: E402
from app.persistence import SQLiteSystemRepository  # noqa: E402
from app.system_store import BUILT_IN_LANGUAGES, SystemStore  # noqa: E402


def _keys(path: Path) -> list[str]:
    """All dictionary keys defined in a locale module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Dict):
            return [key.value for key in node.value.keys if isinstance(key, ast.Constant)]
    raise AssertionError(f"no dictionary in {path}")


def test_no_locale_string_defines_a_regional_variant_or_symbol():
    """No locale key or value refers to a regional symbol option or variant of French."""
    for name in ("en_us", "fr_ca"):
        path = ROOT / f"api/app/locales/{name}.py"
        assert not [key for key in _keys(path) if "quebec" in key.lower()], name
        text = path.read_text(encoding="utf-8").lower()
        for word in ("québec", "quebec", "québécois", "fleur"):
            assert word not in text, f"{name} still contains {word!r}"


def test_built_in_names_are_plain_and_flags_are_stored_data():
    """The built-ins are named "English" and "Français" and carry their flag as ordinary data."""
    assert BUILT_IN_LANGUAGES["en-US"]["name"] == "English"
    assert BUILT_IN_LANGUAGES["fr-CA"]["name"] == "Français"
    assert all(language["flag"] for language in BUILT_IN_LANGUAGES.values())


def test_a_blank_flag_is_treated_the_same_for_every_language(tmp_path, monkeypatch):
    """Saving a language with no flag yields the neutral globe, whichever language it is.

    Why: if French fell back to its old flag while German got the globe, the flag would still be
    decided by a code rule. Built-ins and custom languages must behave identically.
    """
    repository = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)
    store = SystemStore()
    for code in ("en-US", "fr-CA"):
        current = store.get_language(code)
        store.put_language(code, name=current["name"], flag="", dictionary=current["dictionary"])
    store.put_language("de-DE", name="Deutsch", flag="", dictionary={"app.name": "DerridAI"})

    assert {store.get_language(code)["flag"] for code in ("en-US", "fr-CA", "de-DE")} == {"🌐"}

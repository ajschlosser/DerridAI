"""Built-in language dictionaries and their usage in the web app.

Why: English and Québec French must stay complete and equivalent, every string the
frontend asks for must exist, and administrator edits to a dictionary must survive
restarts.
How: reads the locale modules with `ast` (no import) and scans web sources with
regular expressions; the last test uses a temporary SQLite system repository.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _translation_dicts() -> dict[str, dict[str, str]]:
    """Load EN_US and FR_CA from the locale modules without importing them."""
    def load(path: Path, variable: str) -> dict[str, str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                value = node.value
                if isinstance(target, ast.Name) and target.id == variable:
                    return ast.literal_eval(value)
        raise AssertionError(f"{variable} not found in {path}")
    return {
        "DEFAULT_EN_US": load(ROOT / "api/app/locales/en_us.py", "EN_US"),
        "DEFAULT_FR_CA": load(ROOT / "api/app/locales/fr_ca.py", "FR_CA"),
    }










def test_english_and_quebec_french_dictionaries_are_complete_and_placeholder_safe():
    """Same keys in both languages, correct French name, matching numbers and {placeholders}.

    Every English value's {placeholder} names must appear in the French value, and the
    numbers in vector.sync_behavior_help must agree.
    """
    dictionaries = _translation_dicts()
    english = dictionaries["DEFAULT_EN_US"]
    french = dictionaries["DEFAULT_FR_CA"]
    assert len(english) >= 1500
    assert set(english) == set(french)
    assert french["language.french_ca"] == "Français (Québec)"
    assert "500" in french["vector.sync_behavior_help"]
    assert re.findall(r"\d+", english["vector.sync_behavior_help"]) == re.findall(r"\d+", french["vector.sync_behavior_help"])
    for key, source in english.items():
        source_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", source))
        target_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", french[key]))
        assert source_slots == target_slots, key


def test_all_literal_i18n_keys_used_by_web_code_exist_in_both_builtins():
    """Every literal key passed to i18n.t / tf / tr in web/src exists in both languages.

    Legacy context-free keys (e.g. ui.cancel) resolve through the alias table in
    web/src/stores/i18n.ts, so an alias satisfies a used key provided its shared target
    exists in both dictionaries. Limitation: keys built dynamically in code (template
    strings) cannot be found by this regex scan.
    """
    dictionaries = _translation_dicts()
    english = dictionaries["DEFAULT_EN_US"]
    french = dictionaries["DEFAULT_FR_CA"]
    used: set[str] = set()
    patterns = [
        re.compile(r"\bi18n\.(?:t|tf)\(\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"\btrf?\(\s*['\"]([^'\"]+)['\"]"),
    ]
    for path in (ROOT / "web/src").rglob("*"):
        if path.suffix not in {".vue", ".ts", ".js"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            used.update(pattern.findall(text))
    # Context-free labels are aliased to shared `common.*` keys in the i18n store
    # (legacy keys resolve there first). A used key is satisfied by its alias
    # target, and every alias target must itself exist in both dictionaries.
    aliases = dict(re.findall(
        r'"([^"]+)":\s*"(common\.[^"]+)"',
        (ROOT / "web/src/stores/i18n.ts").read_text(encoding="utf-8"),
    ))
    assert aliases, "COMMON_KEY_ALIASES not found in web/src/stores/i18n.ts"
    assert set(aliases.values()) - set(english) == set()
    assert set(aliases.values()) - set(french) == set()
    used = {aliases.get(key, key) for key in used}
    assert used - set(english) == set()
    assert used - set(french) == set()




def test_builtin_dictionaries_bootstrap_current_values_and_preserve_admin_edits(tmp_path, monkeypatch):
    """A fresh database gets the built-in languages; an admin edit survives a new store.

    After editing fr-CA "app.subtitle" and creating a new SystemStore on the same
    database, the custom text is still there (built-ins do not overwrite admin edits).
    """
    import app.system_store as store_module
    from app.persistence import SQLiteSystemRepository

    repository = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)

    store = store_module.SystemStore()
    fresh = store.snapshot()
    assert fresh["languages"]["fr-CA"]["name"] == "Français (Québec)"
    assert fresh["languages"]["en-US"]["dictionary"]["app.name"] == "DerridAI"
    assert fresh["languages"]["fr-CA"]["dictionary"]["nav.rag"] == "Recherche"

    fr = store.get_language("fr-CA")
    dictionary = dict(fr["dictionary"])
    dictionary["app.subtitle"] = "Mon libellé personnalisé"
    store.put_language("fr-CA", name=fr["name"], flag=fr["flag"], dictionary=dictionary)

    preserved = store_module.SystemStore().snapshot()
    assert preserved["languages"]["fr-CA"]["dictionary"]["app.subtitle"] == "Mon libellé personnalisé"



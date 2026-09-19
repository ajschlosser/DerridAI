"""Locale completeness and accessibility floor.

Why: English (en-US) and Québec French (fr-CA) are both first-class. Every string
must exist in both with the same {placeholders}, and no UI text may be smaller than
12px (WCAG readability requirement in AGENTS.md).
How: parses the locale modules with `ast` (no import) and scans CSS/Vue sources
with regular expressions.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"
EN_PATH = ROOT / "api" / "app" / "locales" / "en_us.py"
FR_PATH = ROOT / "api" / "app" / "locales" / "fr_ca.py"


def _locale(path: Path, name: str) -> dict[str, str]:
    """Read one locale dictionary (e.g. EN_US) from a locale file without importing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return value
    raise AssertionError(f"{name} not found in {path}")


def test_built_in_locales_are_canonical_and_complete():
    """en_us and fr_ca have identical keys, non-empty values, and matching placeholders.

    Checks: at least 3000 keys; the two key sets are equal; the French language name is
    "Français (Québec)"; every value is non-blank; and each key's {placeholder} names
    match between languages (so a translation cannot drop or rename a variable).
    """
    en = _locale(EN_PATH, "EN_US")
    fr = _locale(FR_PATH, "FR_CA")
    assert len(en) >= 3000
    assert set(en) == set(fr)
    assert fr["language.french_ca"] == "Français (Québec)"
    assert "Québec" in FR_PATH.read_text(encoding="utf-8")
    for key, source in en.items():
        assert source.strip(), key
        assert fr[key].strip(), key
        source_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", source))
        target_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", fr[key]))
        assert source_slots == target_slots, key




def test_no_explicit_frontend_font_size_is_below_twelve_pixels():
    """No explicit font-size under 12px (rem values are converted at 16px).

    Scans style.css and every .vue file. On failure the message lists file:line for
    each offender, so fixing it means raising that size.
    """
    pattern = re.compile(r"font-size\s*:\s*([0-9.]+)(px|rem)")
    offenders: list[str] = []
    paths = [ROOT / "web/src/style.css", *WEB.rglob("*.vue")]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            value = float(match.group(1))
            pixels = value if match.group(2) == "px" else value * 16
            if pixels < 12:
                offenders.append(f"{path.relative_to(ROOT)}:{text.count(chr(10), 0, match.start()) + 1}")
    assert offenders == []





"""The CSS-to-tokens migration tool: the mappings that earlier versions got wrong.

Why: the tool (scripts/migrate-css-tokens.py) is a heuristic. Each case below is a mistake it
made on the real stylesheet and was caught only by comparing screenshots, so they are pinned.
How: import the script by path (its name has a hyphen) and call its functions directly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("migrate_css_tokens", ROOT / "scripts" / "migrate-css-tokens.py")
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def run(css: str) -> str:
    tool.stats.clear()
    tool.left.clear()
    return tool.process_css(css)


def test_near_black_text_with_a_slight_cast_stays_neutral_text():
    """#26342c is very dark green-grey text, not an "ok" status colour (it once turned green)."""
    assert run(".field input{color:#26342c}") == ".field input{color:var(--text)}"


def test_warm_off_white_is_a_neutral_surface_not_a_warning_tint():
    """#f7f5f1 has almost no chroma; reading it by HLS saturation made it a yellow tone."""
    assert run(".panel{background:#f7f5f1}") == ".panel{background:var(--soft)}"


def test_a_tint_inside_a_status_named_rule_takes_that_tone():
    """A faint warm tint means "warning" only because of the selector (.risk)."""
    out = run(".finding.risk{border-color:#eadfce;background:#fffcf7}")
    assert "background:var(--tone-warn-bg)" in out
    assert "border-color:var(--tone-warn-edge)" in out


def test_pale_hairlines_stay_hairlines_and_do_not_become_status_outlines():
    assert run(".card{border:1px solid #dce5e0}") == ".card{border:1px solid var(--line)}"


def test_accent_used_as_text_becomes_the_readable_accent_and_fills_are_untouched():
    assert run(".a{color:var(--accent)}.b{background:var(--accent)}") == ".a{color:var(--accent-fg)}.b{background:var(--accent)}"
    assert run(".a{color:var(--ui-accent,#355f52)}") == ".a{color:var(--accent-fg)}"


def test_white_is_a_surface_as_a_background_and_a_knockout_as_text():
    out = run(".a{background:#fff}.b{color:#fff}")
    assert out == ".a{background:var(--card)}.b{color:var(--accent-on)}"


def test_fallbacks_shadows_dark_fills_and_pale_text_are_left_alone():
    css = ".a{color:var(--x,#123456)}.b{box-shadow:0 1px #123456}.c{background:#17233b}.d{color:#eeeeee}"
    assert run(css) == css
    assert tool.left  # reported for hand review, not silently dropped


def test_font_sizes_become_rem_and_anything_under_12px_is_left_alone():
    assert run(".a{font-size:13px}.b{font-size:12.5px}.c{font-size:11px}") == ".a{font-size:0.8125rem}.b{font-size:0.78125rem}.c{font-size:11px}"


def test_it_is_idempotent(tmp_path: Path):
    """Running it on its own output changes nothing, so it is safe to re-run over a whole tree."""
    once = run(".a{color:#40516b;background:#f7f5f1;font-size:14px}.risk{background:#fffcf7}")
    assert run(once) == once


def test_dry_run_does_not_write(tmp_path: Path):
    path = tmp_path / "x.css"
    path.write_text(".a{color:#40516b}", encoding="utf-8")
    assert tool.migrate(path, apply=False) is True
    assert path.read_text(encoding="utf-8") == ".a{color:#40516b}"
    assert tool.migrate(path, apply=True) is True
    assert path.read_text(encoding="utf-8") == ".a{color:var(--text-2)}"

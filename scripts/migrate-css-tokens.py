#!/usr/bin/env python3
# Copyright 2026 Aaron John Schlosser, PhD.
"""Rewrite literal colours and px font sizes in CSS and Vue styles to design tokens.

Why: hard-coded hex colours cannot follow dark mode, increased contrast or forced colors.
The tokens they should be are in web/src/styles/tokens.css (see docs/DESIGN_TOKENS.md).

How: each declaration is read together with its selector, and a colour is mapped by what it
does, not just how it looks:
  - by property: text (color, fill, stroke), background, or outline (border, outline)
  - by hue and lightness: a neutral, or an info / ok / warn / danger tone
  - by selector: a tint inside a rule named .risk, .warn, .error, .ok and so on takes that tone
Dark or saturated fills, colours inside a var() fallback, shadows, and gradients other than
backgrounds are left alone and counted as "left for hand review". font-size in px becomes rem
(sizes under 12px are left alone). Accent colours used as text become var(--accent-fg).

Usage (from the repository root; a dry run unless --apply is given):

    python3 scripts/migrate-css-tokens.py web/src/style.css web/src/components/Foo.vue
    python3 scripts/migrate-css-tokens.py --apply $(find web/src/components -name '*.vue')

It is a heuristic. It does not handle rgba()/hsl() or opacity, so review the diff, then check
the result in light and dark: run the token and usage tests and the Corpus Builder theme sweep,
and look at the screens (axe cannot judge text over a gradient).
"""

from __future__ import annotations

import argparse
import colorsys
import collections
import re
from pathlib import Path

# Solid accent greens used as the app's brand colour: text becomes --accent-fg, fills --ui-accent.
ACCENTS = {"#355f52", "#315843", "#315f50", "#294c41", "#466b5b", "#527c70", "#2f5f4c", "#3d6b5a"}
TEXT_PROPERTIES = {
    "color",
    "-webkit-text-fill-color",
    "fill",
    "stroke",
    "caret-color",
    "text-decoration-color",
    "accent-color",
}
# A selector containing one of these words says what a tinted colour inside it means.
SELECTOR_HINTS = [
    ("danger", re.compile(r"error|danger|fail|reject|invalid|blocked|critical|destructive")),
    ("warn", re.compile(r"warn|risk|attention|caution|stalled|unsupported|unresolved|needs-")),
    ("ok", re.compile(r"success|\bok\b|-ok\b|ready|complete|passed|accepted|healthy")),
    ("info", re.compile(r"\binfo\b|-info\b|note\b")),
]
TONE_HUE = {
    "danger": lambda hue: hue < 22 or hue > 335,
    "warn": lambda hue: 22 <= hue < 70,
    "ok": lambda hue: 70 <= hue < 175,
    "info": lambda hue: 175 <= hue < 270,
}

HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
DECLARATION = re.compile(r"([a-zA-Z-]+)(\s*:\s*)([^;{}]+)")
ACCENT_TEXT = re.compile(
    r"\s*var\(--(?:accent|accent-2|ui-accent|ui-accent-dark)"
    r"(?:\s*,\s*(?:#[0-9a-fA-F]{3,6}|var\(--[a-z0-9-]+\)))?\)\s*(?:!important)?\s*"
)

stats: collections.Counter[str] = collections.Counter()
left: collections.Counter[str] = collections.Counter()


def parse_hex(value: str) -> tuple[str, list[float]]:
    """Normalise #rgb / #rrggbb to lower-case #rrggbb and 0..1 channels."""
    value = value.lower()
    if len(value) == 4:
        value = "#" + "".join(c * 2 for c in value[1:])
    return value, [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]


def role_of(prop: str) -> str | None:
    """What a colour is for: text ("fg"), a background ("bg"), or an outline ("border")."""
    prop = prop.lower()
    if prop in TEXT_PROPERTIES:
        return "fg"
    if prop.startswith("background"):
        return "bg"
    if prop.startswith("border") or prop.startswith("outline"):
        return "border"
    return None


def hint_for(selector: str) -> str | None:
    selector = selector.lower()
    for tone, pattern in SELECTOR_HINTS:
        if pattern.search(selector):
            return tone
    return None


def token_for(hex_value: str, prop: str, selector: str = "") -> str | None:
    """The token that a literal colour should become, or None to leave it as written."""
    normal, rgb = parse_hex(hex_value)
    role = role_of(prop)
    if role is None:
        return None
    hue_unit, lightness, saturation = colorsys.rgb_to_hls(*rgb)
    hue = hue_unit * 360
    chroma = max(rgb) - min(rgb)
    if normal == "#ffffff":
        return {"bg": "var(--card)", "fg": "var(--accent-on)", "border": "var(--card)"}[role]
    if role == "bg" and lightness < 0.85:
        return None  # a dark or saturated fill stays as designed
    if role == "fg" and lightness > 0.6:
        return None  # pale text sits on a dark fill
    if normal in ACCENTS:
        return {"fg": "var(--accent-fg)", "bg": "var(--ui-accent)", "border": "var(--ui-accent-border)"}[role]

    hint = hint_for(selector)
    if hint and TONE_HUE[hint](hue) and chroma >= 0.03 and not (role == "fg" and chroma > 0.5):
        if role == "bg" and lightness >= 0.85:
            return f"var(--tone-{hint}-bg)"
        if role == "border":
            return f"var(--tone-{hint}-edge)" if lightness >= 0.62 else f"var(--tone-{hint}-border)"
        if role == "fg":
            return f"var(--tone-{hint}-fg)"

    neutral = (
        chroma < 0.035
        or (lightness < 0.6 and saturation < 0.12)
        or lightness < 0.04
        or (role == "fg" and lightness < 0.4 and chroma < 0.14)  # near-black with a slight cast is still text
        or (195 <= hue <= 240 and saturation < 0.5)  # blue-grey "slate" neutrals
    )
    if neutral:
        if role == "fg":
            return "var(--text)" if lightness < 0.22 else ("var(--text-2)" if lightness < 0.42 else "var(--muted)")
        if role == "bg":
            return "var(--card)" if lightness >= 0.97 else "var(--soft)"
        return "var(--line)" if lightness >= 0.7 else "var(--line-strong)"
    if role == "border" and lightness >= 0.78 and chroma < 0.12:
        return "var(--line)"  # a pale hairline, not a status outline
    if role == "fg" and chroma > 0.5:
        return None  # a saturated link or brand colour

    if hue < 22 or hue > 335:
        tone = "danger"
    elif hue < 70:
        tone = "warn"
    elif hue < 175:
        tone = "ok"
    else:
        tone = "info"
    if role == "border" and lightness >= 0.62:
        return f"var(--tone-{tone}-edge)"
    return f"var(--tone-{tone}-{role})"


def rewrite_value(prop: str, value: str, selector: str) -> str:
    if prop.lower() in {"color", "fill", "stroke"} and ACCENT_TEXT.fullmatch(value):
        stats["accent-text"] += 1
        lead = value[: len(value) - len(value.lstrip())]
        return lead + "var(--accent-fg)" + (" !important" if "!important" in value else "")

    fallbacks = [(m.start(), m.end()) for m in re.finditer(r"var\([^)]*\)", value)]
    lowered = value.lower()
    edits: list[tuple[int, int, str]] = []
    for match in HEX.finditer(value):
        if any(start <= match.start() < end for start, end in fallbacks):
            continue  # the fallback of a var(): leave it
        literal = f"{prop}:{match.group(0).lower()}"
        if "shadow" in prop.lower() or ("gradient" in lowered and not prop.lower().startswith("background")):
            left[literal] += 1
            continue
        token = token_for(match.group(0), prop, selector)
        if token is None:
            left[literal] += 1
            continue
        edits.append((match.start(), match.end(), token))
        stats["colour"] += 1
    for start, end, token in reversed(edits):
        value = value[:start] + token + value[end:]

    if prop.lower() == "font-size":

        def to_rem(match: re.Match[str]) -> str:
            pixels = float(match.group(1))
            if pixels < 12:
                left[f"font-size:{pixels}px"] += 1
                return match.group(0)
            stats["font-size"] += 1
            return f"{round(pixels / 16, 5):g}rem"

        value = re.sub(r"(?<![\d.])(\d+(?:\.\d+)?)px\b", to_rem, value)
    return value


def process_css(css: str) -> str:
    """Rewrite every declaration block in a stylesheet, passing its selector along."""

    def rewrite_block(match: re.Match[str]) -> str:
        selector, body = match.group(1), match.group(2)
        body = DECLARATION.sub(
            lambda d: d.group(1) + d.group(2) + rewrite_value(d.group(1), d.group(3), selector), body
        )
        return selector + "{" + body + "}"

    return re.sub(r"([^{}]*)\{([^{}]*)\}", rewrite_block, css)


def migrate(path: Path, apply: bool) -> bool:
    """Migrate one .css or .vue file. Returns True if it would change (or did change)."""
    source = path.read_text(encoding="utf-8")
    if path.suffix == ".css":
        migrated = process_css(source)
    else:
        migrated = re.sub(
            r"(<style[^>]*>)(.*?)(</style>)",
            lambda m: m.group(1) + process_css(m.group(2)) + m.group(3),
            source,
            flags=re.S,
        )
    if migrated == source:
        return False
    if apply:
        path.write_text(migrated, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rewrite literal colours and px font sizes to design tokens.")
    parser.add_argument("files", nargs="+", type=Path, help=".css or .vue files")
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    args = parser.parse_args(argv)
    stats.clear()
    left.clear()
    changed = [path for path in args.files if migrate(path, args.apply)]
    verb = "changed" if args.apply else "would change"
    print(f"files {verb}: {len(changed)} of {len(args.files)}  {dict(stats)}")
    print(f"left for hand review: {len(left)} distinct, e.g. {left.most_common(8)}")
    if changed and not args.apply:
        print("dry run: re-run with --apply to write the changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

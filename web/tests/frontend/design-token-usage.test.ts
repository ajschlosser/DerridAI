import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Ratchet: literal colours in declarations cannot be themed, so they are what breaks dark mode,
// increased contrast and forced colours. The remaining ones are theme-independent solid fills
// (status dots, solid badges). Use a token from src/styles/tokens.css instead of adding one. When
// you remove a literal, lower these numbers; they must never go up. The views have none left, so
// they must stay at zero.
const MAX_LITERALS = { components: 26, views: 0, stylesheet: 88 };

const hexColour = /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g;
const declaration = /(-{0,2}[a-zA-Z][a-zA-Z-]*)\s*:\s*([^;{}]+)/g;

function literalsIn(css: string): number {
  let total = 0;
  for (const block of css.matchAll(/\{([^{}]*)\}/g)) {
    for (const decl of block[1].matchAll(declaration)) {
      if (decl[1].startsWith("--")) continue; // token definitions are where literals belong
      total += (decl[2].replace(/var\([^)]*\)/g, "").match(hexColour) || []).length;
    }
  }
  return total;
}
// A translucent white background is a pale slab on a dark surface. Mix the card colour instead:
// color-mix(in srgb, var(--card) 82%, transparent).
const whiteOverlayBackground =
  /background(?:-color)?\s*:\s*rgba?\(\s*255\s*[, ]\s*255\s*[, ]\s*255\s*[,/]/;

function vueFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? vueFiles(path) : path.endsWith(".vue") ? [path] : [];
  });
}

describe("design token usage", () => {
  it("does not add literal colours to component styles", () => {
    const total = vueFiles("src/components")
      .flatMap((file) =>
        [...readFileSync(file, "utf8").matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) =>
          literalsIn(m[1]),
        ),
      )
      .reduce((a, b) => a + b, 0);
    expect(total).toBeLessThanOrEqual(MAX_LITERALS.components);
  });
  it("keeps the views free of literal colours", () => {
    const total = vueFiles("src/views")
      .flatMap((file) =>
        [...readFileSync(file, "utf8").matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) =>
          literalsIn(m[1]),
        ),
      )
      .reduce((a, b) => a + b, 0);
    expect(total).toBeLessThanOrEqual(MAX_LITERALS.views);
  });
  it("uses no translucent-white backgrounds", () => {
    const sources = [...vueFiles("src/components"), ...vueFiles("src/views"), "src/style.css"];
    const offenders = sources.filter((file) =>
      whiteOverlayBackground.test(readFileSync(file, "utf8")),
    );
    expect(offenders).toEqual([]);
  });
  it("does not add literal colours to the global stylesheet", () => {
    expect(literalsIn(readFileSync("src/style.css", "utf8"))).toBeLessThanOrEqual(
      MAX_LITERALS.stylesheet,
    );
  });
});

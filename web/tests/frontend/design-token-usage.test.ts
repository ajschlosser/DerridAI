import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Ratchet: literal colours in declarations cannot be themed, so they are what breaks dark mode,
// increased contrast and forced colours. The remaining ones are theme-independent solid fills
// (status dots, solid badges). Use a token from src/styles/tokens.css instead of adding one. When
// you remove a literal, lower these numbers; they must never go up.
const MAX_LITERALS = { components: 27, stylesheet: 89 };

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
  it("does not add literal colours to the global stylesheet", () => {
    expect(literalsIn(readFileSync("src/style.css", "utf8"))).toBeLessThanOrEqual(
      MAX_LITERALS.stylesheet,
    );
  });
});

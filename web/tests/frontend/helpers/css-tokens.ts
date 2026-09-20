import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Contrast tests read colours straight from the CSS. Rules now say var(--muted) rather than a hex,
// so these helpers resolve a value to the light-theme colour the token stands for.
const read = (path: string) => readFileSync(resolve(process.cwd(), path), "utf8");

// Blocks whose selector is the default (light) scope. Later definitions win, as in the cascade.
const LIGHT_SCOPES = new Set([":root", ':root,[data-ui-theme="green"]']);
function lightDefinitions(source: string, into: Map<string, string>) {
  const css = source.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const block of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (!LIGHT_SCOPES.has(block[1].replace(/\s+/g, "").trim())) continue;
    for (const decl of block[2].matchAll(/(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);?/g))
      into.set(decl[1], decl[2].trim());
  }
}
export function lightTokens(extraCss = ""): Map<string, string> {
  const tokens = new Map<string, string>();
  for (const css of [read("src/style.css"), read("src/styles/tokens.css"), extraCss])
    lightDefinitions(css, tokens);
  return tokens;
}

/** Resolve a colour value (a hex, or a var() chain with optional fallbacks) to #rrggbb. */
export function resolveHex(value: string, tokens: Map<string, string> = lightTokens()): string {
  let current = value.trim();
  for (let depth = 0; depth < 12; depth++) {
    const ref = current.match(/^var\(\s*(--[a-zA-Z0-9-]+)\s*(?:,\s*(.+))?\)$/);
    if (!ref) break;
    current = (tokens.get(ref[1]) ?? ref[2] ?? "").trim();
  }
  const hex = current.match(/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
  if (!hex) throw new Error(`Cannot resolve "${value}" to a colour (got "${current}")`);
  const digits = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join("") : hex[1];
  return `#${digits.toLowerCase()}`;
}

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// The tokens are CSS, so the contrast guarantees are checked against the CSS itself. If a token
// value changes, this fails before an unreadable colour pair ships.
const tokens = readFileSync("src/styles/tokens.css", "utf8");
const styles = readFileSync("src/style.css", "utf8");

function block(css: string, opener: string): string {
  const start = css.indexOf(opener);
  if (start < 0) throw new Error(`No block for ${opener}`);
  const open = css.indexOf("{", start);
  let depth = 0;
  for (let i = open; i < css.length; i++) {
    if (css[i] === "{") depth++;
    if (css[i] === "}" && --depth === 0) return css.slice(open + 1, i);
  }
  throw new Error(`Unclosed block for ${opener}`);
}
function value(css: string, name: string): string {
  const match = css.match(new RegExp(`${name}\\s*:\\s*([^;]+);`));
  if (!match) throw new Error(`Missing ${name}`);
  return match[1].trim();
}
type RGB = [number, number, number];
const hex = (h: string): RGB => {
  const s = h.replace("#", "");
  const full = s.length === 3 ? [...s].map((c) => c + c).join("") : s;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16)) as RGB;
};
// color-mix(in srgb, <a> <pct>%, <b>) interpolates the channels directly.
const mix = (a: RGB, pct: number, b: RGB): RGB =>
  a.map((c, i) => c * (pct / 100) + b[i] * (1 - pct / 100)) as RGB;
const luminance = ([r, g, b]: RGB) => {
  const f = (c: number) => ((c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const contrast = (a: RGB, b: RGB) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const light = block(tokens, ":root {");
const dark = block(tokens, 'html[data-color-scheme="dark"] {');
const darkNeutrals = block(styles, 'html[data-color-scheme="dark"]{');
const surfaces = { light: hex("#ffffff"), dark: hex(value(darkNeutrals, "--card")) };
const themes = ["green", "blue", "slate"].map((name) => {
  const rule = block(styles, `[data-ui-theme="${name}"]{`);
  return {
    name,
    accent: hex(value(rule, "--ui-accent")),
    accentDark: hex(value(rule, "--ui-accent-dark")),
  };
});

describe("status tones", () => {
  for (const [scheme, css] of [
    ["light", light],
    ["dark", dark],
  ] as const) {
    for (const tone of ["info", "ok", "warn", "danger"]) {
      const fg = hex(value(css, `--tone-${tone}-fg`));
      const bg = hex(value(css, `--tone-${tone}-bg`));
      const border = hex(value(css, `--tone-${tone}-border`));
      it(`${scheme} ${tone}: text on its tint is at least 4.5:1`, () => {
        expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
      });
      it(`${scheme} ${tone}: text on the surface is at least 4.5:1`, () => {
        expect(contrast(fg, surfaces[scheme])).toBeGreaterThanOrEqual(4.5);
      });
      it(`${scheme} ${tone}: the outline is at least 3:1 against the surface`, () => {
        expect(contrast(border, surfaces[scheme])).toBeGreaterThanOrEqual(3);
      });
    }
  }
});

describe("accent as text", () => {
  for (const { name, accent, accentDark } of themes) {
    it(`${name} theme, light: accent text on the surface is at least 4.5:1`, () => {
      expect(contrast(accentDark, surfaces.light)).toBeGreaterThanOrEqual(4.5);
    });
    it(`${name} theme, dark: accent text on the surface and on the soft accent fill is at least 4.5:1`, () => {
      const fg = mix(accent, 40, [255, 255, 255]);
      expect(contrast(fg, surfaces.dark)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(fg, mix(accent, 34, surfaces.dark))).toBeGreaterThanOrEqual(4.5);
    });
    it(`${name} theme: white text on the solid accent is at least 4.5:1`, () => {
      expect(contrast(hex("#ffffff"), accent)).toBeGreaterThanOrEqual(4.5);
    });
  }
});

describe("highlighter", () => {
  it("dark text on the highlight fill is at least 4.5:1, and the pair is the same in both schemes", () => {
    expect(
      contrast(hex(value(light, "--mark-fg")), hex(value(light, "--mark-bg"))),
    ).toBeGreaterThanOrEqual(4.5);
    expect(dark).not.toMatch(/--mark-(bg|fg)/); // a highlighter does not change with the theme
  });
});

describe("neutral text steps", () => {
  it("secondary text meets 4.5:1 on the surface in both schemes", () => {
    expect(contrast(hex(value(light, "--text-2")), surfaces.light)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hex(value(dark, "--text-2")), surfaces.dark)).toBeGreaterThanOrEqual(4.5);
  });
  it("the dark focus ring is at least 3:1 against the dark surface", () => {
    expect(contrast(hex(value(dark, "--focus-ring")), surfaces.dark)).toBeGreaterThanOrEqual(3);
  });
});

describe("type scale", () => {
  it("never goes below 12px and is expressed in rem", () => {
    for (const match of light.matchAll(/--fs-[a-z0-9]+\s*:\s*([\d.]+)rem/g)) {
      expect(parseFloat(match[1]) * 16).toBeGreaterThanOrEqual(12);
    }
    expect(light.match(/--fs-/g)?.length).toBeGreaterThanOrEqual(7);
  });
});

describe("unified workbench contract", () => {
  it("defines semantic surfaces, text, borders, controls, and focus tokens", () => {
    for (const name of [
      "surface-page",
      "surface-card",
      "surface-raised",
      "surface-inset",
      "surface-overlay",
      "surface-hover",
      "surface-selected",
      "text-primary",
      "text-secondary",
      "text-tertiary",
      "border-subtle",
      "border-strong",
      "border-interactive",
      "control-height",
      "control-height-small",
      "radius-control",
      "radius-card",
      "radius-overlay",
      "shadow-card",
      "shadow-overlay",
      "scrim",
      "focus-ring-width",
      "focus-ring-offset",
    ]) {
      expect(light).toMatch(new RegExp(`--${name}\\s*:`));
    }
  });
});

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Home-page and sign-in colours that axe cannot judge (glyph-only icons, small dots) or that once failed.
// WCAG 1.4.3 text >= 4.5:1, 1.4.11 icons and state indicators >= 3:1, 2.5.8 targets >= 24px.
const css = readFileSync(resolve(process.cwd(), "src/style.css"), "utf8");
const rule = (selector: string): string => {
  const match = css.match(
    new RegExp(`${selector.replace(/[.[\]()]/g, "\\$&")}\\s*\\{([^}]*)\\}`, "g"),
  );
  if (!match) throw new Error(`rule ${selector} not found`);
  return match.join(" ");
};
const declared = (selector: string, property: string): string => {
  const found = [
    ...rule(selector).matchAll(new RegExp(`(?:^|[;{\\s])${property}:\\s*([^;}]+)`, "g")),
  ].map((m) => m[1].trim());
  if (!found.length) throw new Error(`${selector} does not set ${property}`);
  return found[found.length - 1];
};
const rgb = (hex: string): [number, number, number] =>
  [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
const channel = (v: number) => {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};
const luminance = (c: [number, number, number]) =>
  0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2]);
const ratio = (a: string, b: string) => {
  const [hi, lo] = [luminance(rgb(a)), luminance(rgb(b))].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

describe("Home page and sign-in contrast", () => {
  it("the sign-in subtitle is readable text", () => {
    expect(ratio(declared(".auth-brand-lockup span", "color"), "#ffffff")).toBeGreaterThanOrEqual(
      4.5,
    );
  });

  it("dashboard helper text and the empty record hint are readable", () => {
    for (const selector of [
      ".dashboard-metric-controls",
      ".dashboard-quick-field span",
      ".dashboard-record-empty",
    ]) {
      expect(ratio(declared(selector, "color"), "#ffffff"), selector).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("the sidebar collapse arrow is a full-opacity icon at least 3:1 and 24px square", () => {
    const toggle = ".sidebar-toggle";
    expect(ratio(declared(toggle, "color"), "#ffffff")).toBeGreaterThanOrEqual(3);
    expect(css.match(/\.sidebar-toggle\{[^}]*opacity:\s*\.5/)).toBeNull(); // opacity lowers the effective contrast
    expect(parseFloat(declared(toggle, "width"))).toBeGreaterThanOrEqual(24);
    expect(parseFloat(declared(toggle, "height"))).toBeGreaterThanOrEqual(24);
  });

  it("carousel dots are 24px targets that draw a dot at least 3:1 against white", () => {
    const dot = ".dashboard-metric-dots button";
    expect(parseFloat(declared(dot, "width"))).toBeGreaterThanOrEqual(24);
    expect(parseFloat(declared(dot, "height"))).toBeGreaterThanOrEqual(24);
    expect(declared(dot, "background-clip")).toBe("content-box"); // the padding is the hit area, not more dot
    expect(ratio(declared(dot, "background"), "#ffffff")).toBeGreaterThanOrEqual(3);
  });
});

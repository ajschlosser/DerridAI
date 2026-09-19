import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// WCAG 1.4.3 (text >= 4.5:1) and 1.4.11 (UI components and graphics >= 3:1) for every colour pair the
// Operations panel uses. axe cannot judge count badges, gradients, or non-text contrast, so the tokens
// are checked here directly from the component's own stylesheet.
const source = readFileSync(resolve(process.cwd(), "src/components/OperationsPanel.vue"), "utf8");
// Rules are matched against a whitespace-free copy so the checks survive any formatter.
const compact = source.replace(/\s+/g, "");
const token = (name: string): string => {
  const match = source.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{3,6})\\b`));
  if (!match) throw new Error(`token --${name} not found`);
  const hex = match[1];
  return hex.length === 4 ? `#${[...hex.slice(1)].map((c) => c + c).join("")}` : hex;
};
const rgb = (hex: string): [number, number, number] =>
  [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
const channel = (v: number) => {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};
const luminance = (c: [number, number, number]) =>
  0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2]);
const ratio = (a: [number, number, number], b: [number, number, number]) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

// The three accent themes from Settings (style.css). The panel takes its accent from them.
const ACCENTS: Record<string, string> = { green: "#355f52", blue: "#0b67e8", slate: "#4d6076" };
const WHITE = rgb("#ffffff");

describe("Operations panel contrast", () => {
  it.each(["text", "muted"])(
    "--ops-%s is readable on the surface and on the sunken background",
    (name) => {
      expect(ratio(rgb(token(`ops-${name}`)), rgb(token("ops-surface")))).toBeGreaterThanOrEqual(
        4.5,
      );
      expect(ratio(rgb(token(`ops-${name}`)), rgb(token("ops-sunken")))).toBeGreaterThanOrEqual(
        4.5,
      );
    },
  );

  it.each(["info", "success", "warning", "danger", "neutral"])(
    "%s text on its tint is at least 4.5:1",
    (tone) => {
      expect(
        ratio(rgb(token(`ops-${tone}-fg`)), rgb(token(`ops-${tone}-bg`))),
      ).toBeGreaterThanOrEqual(4.5);
    },
  );

  it.each(["info", "success", "warning", "danger", "neutral"])(
    "%s text is also readable on plain white (badges over a card)",
    (tone) => {
      expect(ratio(rgb(token(`ops-${tone}-fg`)), WHITE)).toBeGreaterThanOrEqual(4.5);
    },
  );

  it.each(Object.entries(ACCENTS))(
    "on the %s theme, white on the accent (pressed chip, primary button) is at least 4.5:1",
    (_name, accent) => {
      expect(ratio(WHITE, rgb(accent))).toBeGreaterThanOrEqual(4.5);
    },
  );

  it("the count inside a pressed chip is solid white with accent text, not a translucent overlay", () => {
    // A translucent white chip over the accent lowers the contrast of white text below 4.5:1 on every theme.
    expect(compact).toMatch(
      /\.ops-chip\[aria-pressed="true"\]\.ops-chip-count\{background:#fff;color:var\(--ops-accent\);?\}/,
    );
  });

  it.each(Object.entries(ACCENTS))(
    "on the %s theme, accent text and the focus ring are readable on white",
    (_name, accent) => {
      expect(ratio(rgb(accent), WHITE)).toBeGreaterThanOrEqual(4.5);
    },
  );

  it.each(Object.entries(ACCENTS))(
    "on the %s theme, the progress fill is distinguishable from its track (1.4.11)",
    (_name, accent) => {
      const track = rgb(compact.match(/\.ops-progress\{[^}]*background:(#[0-9a-fA-F]{6})/)![1]);
      expect(ratio(rgb(accent), track)).toBeGreaterThanOrEqual(3);
    },
  );

  it("control borders (buttons, chips) are at least 3:1 against the surface (1.4.11)", () => {
    expect(ratio(rgb(token("ops-control")), rgb(token("ops-surface")))).toBeGreaterThanOrEqual(3);
  });

  it("the danger button text is readable on white and on its hover tint", () => {
    expect(ratio(rgb(token("ops-danger-fg")), WHITE)).toBeGreaterThanOrEqual(4.5);
    expect(ratio(rgb(token("ops-danger-fg")), rgb(token("ops-danger-bg")))).toBeGreaterThanOrEqual(
      4.5,
    );
  });
});

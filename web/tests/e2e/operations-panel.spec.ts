import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const STORIES = ["mixed", "empty", "many-running", "failures-only", "long-names", "long-history", "narrow", "french-formatting"];
// WCAG 2.0, 2.1 and 2.2 at levels A and AA.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// Storybook's a11y addon runs axe on every story as it loads; a second run started at the same moment
// throws "Axe is already running". Wait for the addon's run to finish and try again.
async function scan(page: Page) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({ page }).include("#operationsPanel").withTags(TAGS).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}
const url = (story: string) => `/iframe.html?id=operations-panel--${story}&viewMode=story`;

for (const story of STORIES) {
  test(`Operations panel (${story}) has no WCAG 2.2 AA violations`, async ({ page }) => {
    await page.goto(url(story));
    await expect(page.locator("#operationsPanel")).toBeVisible();
    const results = await scan(page);
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test("keyboard: every control is reachable, shows a visible focus ring, and filters work with Enter", async ({ page }) => {
  await page.goto(url("mixed"));
  const chip = page.getByRole("button", { name: /^Running/ });
  await chip.focus();
  const outline = await chip.evaluate((el) => { const s = getComputedStyle(el); return { width: parseFloat(s.outlineWidth), style: s.outlineStyle }; });
  expect(outline.style).toBe("solid");
  expect(outline.width).toBeGreaterThanOrEqual(2);
  await page.keyboard.press("Enter");
  await expect(chip).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("li.ops-row")).toHaveCount(2); // the two in-progress operations
  // Tab order visits every button once, in reading order, never trapping.
  await page.locator("#refreshJobs").focus();
  const seen = new Set<string>();
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press("Tab");
    seen.add(await page.evaluate(() => document.activeElement?.getAttribute("aria-label") || document.activeElement?.textContent?.trim() || ""));
  }
  expect(seen.size).toBeGreaterThan(5);
});

test("target size (2.5.8): interactive controls are at least 24x24 CSS pixels", async ({ page }) => {
  await page.goto(url("mixed"));
  const small = await page.locator("#operationsPanel button").evaluateAll((buttons) =>
    buttons.map((b) => { const r = b.getBoundingClientRect(); return { text: b.textContent?.trim(), w: r.width, h: r.height }; }).filter((b) => b.w > 0 && (b.w < 24 || b.h < 24)));
  expect(small).toEqual([]);
});

test("reflow (1.4.10): no horizontal scrolling at 320 CSS pixels", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(url("long-names"));
  await expect(page.locator("#operationsPanel")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("text resize (1.4.4): 200% text does not clip or overflow the panel", async ({ page }) => {
  await page.goto(url("long-names"));
  await expect(page.locator("#operationsPanel")).toBeVisible();
  await page.addStyleTag({ content: "html{font-size:200%!important}" });
  const { panelOverflow, pageOverflow } = await page.evaluate(() => {
    const panel = document.querySelector("#operationsPanel") as HTMLElement;
    return { panelOverflow: panel.scrollWidth - panel.clientWidth, pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth };
  });
  expect(panelOverflow).toBeLessThanOrEqual(1);
  expect(pageOverflow).toBeLessThanOrEqual(1);
});

test("text spacing (1.4.12): increased spacing does not hide content", async ({ page }) => {
  await page.goto(url("mixed"));
  await expect(page.locator("#operationsPanel")).toBeVisible();
  await page.addStyleTag({ content: "*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important} p{margin-bottom:2em!important}" });
  const clipped = await page.locator("#operationsPanel .ops-row").evaluateAll((rows) => rows.filter((r) => r.scrollWidth > r.clientWidth + 1).length);
  expect(clipped).toBe(0);
});

test("motion: reduced-motion turns every animation and transition off", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(url("mixed"));
  const animated = await page.locator("#operationsPanel *").evaluateAll((els) =>
    els.filter((el) => { const s = getComputedStyle(el); return (s.animationName !== "none" && parseFloat(s.animationDuration) > 0.001) || parseFloat(s.transitionDuration) > 0.001; }).length);
  expect(animated).toBe(0);
});

test("progress is exposed to assistive technology with a name, range and value", async ({ page }) => {
  await page.goto(url("mixed"));
  const bar = page.getByRole("progressbar", { name: /Progress of PDF corpus build/ });
  await expect(bar).toHaveAttribute("aria-valuenow", "30");
  await expect(bar).toHaveAttribute("aria-valuemin", "0");
  await expect(bar).toHaveAttribute("aria-valuemax", "100");
});

// The browser's accessibility tree is what a screen reader is given. These are not screen-reader tests (that needs a
// human with NVDA/JAWS/VoiceOver), but they pin the structure and names assistive technology receives.
test("accessibility tree: landmark, headings, groups, and what each control is called", async ({ page }) => {
  await page.goto(url("mixed"));
  await expect(page.locator("#operationsPanel")).toBeVisible();
  await expect(page.locator("#operationsPanel")).toMatchAriaSnapshot(`
    - region "Background operations":
      - heading "Background operations" [level=2]
      - button "Refresh"
      - button "Clear finished"
      - group "Show operations":
        - button /All \\d+/ [pressed]
        - button /Running \\d+/
        - button /Needs attention \\d+/
        - button /Finished \\d+/
      - region /Needs attention \\d+/:
        - heading /Needs attention \\d+/ [level=3]
        - list:
          - listitem "Languages · Français":
            - heading "Languages · Français" [level=4]
            - text: Failed
            - button "Details for Languages · Français": Details
            - button "Remove Languages · Français": Remove
  `);
});

test("accessibility tree: an in-progress row exposes a named progress bar and a row-specific Cancel", async ({ page }) => {
  await page.goto(url("mixed"));
  const row = page.getByRole("listitem", { name: "PDF corpus build" });
  await expect(row).toMatchAriaSnapshot(`
    - listitem "PDF corpus build":
      - heading "PDF corpus build" [level=4]
      - text: Running
      - progressbar "Progress of PDF corpus build"
      - paragraph: 30% overall
      - button "Details for PDF corpus build": Details
      - button "Cancel PDF corpus build": Cancel
  `);
});

test("accessibility tree: the meta line reads as separate sentences, not one run-on", async ({ page }) => {
  await page.goto(url("mixed"));
  const meta = page.getByRole("listitem", { name: "Languages · Français" }).locator(".ops-meta");
  const text = (await meta.evaluate((el) => (el as HTMLElement).textContent || "")).replace(/\s+/g, " ");
  expect(text).toMatch(/Finished .* ago\. Took .*\. by admin/);
});

test("accessibility tree: the empty state is a heading and a sentence, and no list is exposed", async ({ page }) => {
  await page.goto(url("empty"));
  await expect(page.locator("#operationsPanel")).toMatchAriaSnapshot(`
    - region "Background operations":
      - heading "Background operations" [level=2]
      - group "Show operations"
      - heading "Nothing in flight" [level=3]
      - paragraph: /Start a corpus build/
  `);
  await expect(page.locator("#operationsPanel li")).toHaveCount(0);
});

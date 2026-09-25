import { expect, test } from "@playwright/test";
import { runAxe } from "./support/axe";

function alphaFromCssColor(value: string): number {
  const rgba = value.match(/rgba?\(([^)]+)\)/i);
  if (!rgba) return 1;
  const parts = rgba[1].split(/[\s,/]+/).filter(Boolean);
  if (parts.length < 4) return 1;
  const alpha = Number(parts[3]);
  return Number.isFinite(alpha) ? alpha : 1;
}

async function expectWcag2AA(page: any, include: string) {
  const results = await runAxe(page, (builder) =>
    builder.include(include).withTags(["wcag2a", "wcag2aa"]),
  );
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

test("build summary is an opaque-enough glass surface and WCAG 2.0 AA clean", async ({ page }) => {
  await page.goto("/iframe.html?id=corpus-build-readiness--ready&viewMode=story");
  const surface = page.locator(".build-readiness");
  await expect(surface).toBeVisible();
  const background = await surface.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(alphaFromCssColor(background)).toBeGreaterThanOrEqual(0.9);
  const overflow = await surface.evaluate((el) => ({
    scrollWidth: (el as HTMLElement).scrollWidth,
    clientWidth: (el as HTMLElement).clientWidth,
  }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  await expectWcag2AA(page, ".build-readiness");
});

test("corpus builds popover is opaque, keyboard focusable, and WCAG 2.0 AA clean", async ({
  page,
}) => {
  await page.goto(
    "/iframe.html?id=corpus-builder-workflow-build-history-menu--default&viewMode=story",
  );
  const summary = page.locator(".history-menu > summary");
  await summary.focus();
  await expect(summary).toBeFocused();
  const outline = await summary.evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(outline).not.toBe("none");
  await summary.press("Enter");
  const popover = page.locator(".history-popover");
  await expect(popover).toBeVisible();
  const background = await popover.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(alphaFromCssColor(background)).toBeGreaterThanOrEqual(0.9);
  await expectWcag2AA(page, ".history-menu");
});

test("confident stance is visibly selected in the real Storybook component", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=corpus-builder-review-metadata-field--auto-populated-stance&viewMode=story",
  );
  const select = page.locator("select.control");
  await expect(select).toHaveValue("affirm");
});

test("reviewer-defined structure remains selected in the rendered conflict editor", async ({
  page,
}) => {
  await page.goto(
    "/iframe.html?id=corpus-builder-review-metadata-field--reviewer-structure-conflict&viewMode=story",
  );
  const select = page.locator("select.control");
  await expect(select).toHaveValue("main_text");
  await expect(page.getByText(/Deterministic and LLM suggestions disagree/i)).toBeVisible();
  await expectWcag2AA(page, ".metadata-field");
});

test("normalized stance aliases remain selected and disclose normalization", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=corpus-builder-review-metadata-field--normalized-stance-alias&viewMode=story",
  );
  const select = page.locator("select.control");
  await expect(select).toHaveValue("affirm");
  await expect(page.getByText(/normalized to/i)).toBeVisible();
  await expectWcag2AA(page, ".metadata-field");
});

test("build summary remains usable at 200 percent zoom-equivalent scaling", async ({ page }) => {
  await page.goto("/iframe.html?id=corpus-build-readiness--ready&viewMode=story");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  const surface = page.locator(".build-readiness");
  await expect(surface).toBeVisible();
  const metrics = await surface.evaluate((el) => ({
    scrollWidth: (el as HTMLElement).scrollWidth,
    clientWidth: (el as HTMLElement).clientWidth,
    rect: (el as HTMLElement).getBoundingClientRect().toJSON(),
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
  await expect(page.getByRole("button", { name: /Build record set/i })).toBeVisible();
  await expectWcag2AA(page, ".build-readiness");
});

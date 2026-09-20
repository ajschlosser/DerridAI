import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const STORIES = ["running", "completed-converged", "stopped", "failed", "idle-after-initial"];
// WCAG 2.0, 2.1 and 2.2 at levels A and AA.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const url = (story: string) =>
  `/iframe.html?id=corpus-builder-status-enrichment-pass-status--${story}&viewMode=story`;

// Storybook's a11y addon runs axe as each story loads; wait out its run rather than racing it.
async function scan(page: Page) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({ page }).include(".pass-status").withTags(TAGS).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}

for (const story of STORIES) {
  test(`Enrichment pass status (${story}) has no WCAG 2.2 AA violations`, async ({ page }) => {
    await page.goto(url(story));
    await expect(page.locator(".pass-status")).toBeVisible();
    const results = await scan(page);
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test("running state is a named status region with a labelled progress bar", async ({ page }) => {
  await page.goto(url("running"));
  const region = page.getByRole("status");
  await expect(region).toContainText("Pass 2 of 3 is running");
  await expect(region.getByRole("progressbar")).toHaveAccessibleName(/30 of 60 records/);
  await expect(region.getByRole("button", { name: "Stop enrichment" })).toBeVisible();
});

test("target size (2.5.8): buttons are at least 24x24 CSS pixels in every state", async ({
  page,
}) => {
  for (const story of STORIES) {
    await page.goto(url(story));
    await expect(page.locator(".pass-status")).toBeVisible();
    const small = await page.locator(".pass-status button").evaluateAll((buttons) =>
      buttons
        .map((b) => {
          const r = b.getBoundingClientRect();
          return { text: b.textContent?.trim(), w: r.width, h: r.height };
        })
        .filter((b) => b.w < 24 || b.h < 24),
    );
    expect(small, story).toEqual([]);
  }
});

test("reflow (1.4.10): no horizontal scrolling at 320 CSS pixels", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(url("completed-converged"));
  await expect(page.locator(".pass-status")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});

test("keyboard: the actions are reachable with a visible focus ring", async ({ page }) => {
  await page.goto(url("completed-converged"));
  await page.getByRole("button", { name: "Run another pass" }).focus();
  await expect(page.getByRole("button", { name: "Run another pass" })).toBeFocused();
  const outline = await page
    .getByRole("button", { name: "Run another pass" })
    .evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(outline).not.toBe("none");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Dismiss" })).toBeFocused();
});

test("idle after the first pass offers another pass without a dismiss-only trap", async ({ page }) => {
  await page.goto(url("idle-after-initial"));
  const region = page.getByRole("status");
  await expect(region).toContainText("without reviewing every record");
  await expect(region.getByRole("button", { name: "Run another pass" })).toBeVisible();
  await expect(region.getByRole("button", { name: "Dismiss" })).toHaveCount(0);
});

const dialogUrl =
  "/iframe.html?id=corpus-builder-review-metadata-enrichment-dialog--default&viewMode=story";

test("enrichment dialog Passes control is labelled, keyboard operable, and WCAG 2.2 AA clean", async ({
  page,
}) => {
  await page.goto(dialogUrl);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const passes = dialog.getByRole("group", { name: "Passes" });
  await expect(passes).toBeVisible();
  await expect(dialog.getByRole("spinbutton")).toHaveCount(0);
  await passes.getByRole("radio", { name: "Chain several passes" }).check();
  const count = dialog.getByRole("spinbutton", { name: "Maximum passes" });
  await expect(count).toBeVisible();
  await expect(count).toHaveAttribute("min", "2");
  await expect(count).toHaveAttribute("max", "10");
  for (let attempt = 0; ; attempt++) {
    try {
      const results = await new AxeBuilder({ page })
        .include('[role="dialog"]')
        .withTags(TAGS)
        .analyze();
      expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
      break;
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
});

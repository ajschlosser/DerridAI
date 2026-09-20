import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const STORIES = [
  ["settings-save-state", "unsaved", ".settings-save-state"],
  ["settings-save-state", "failed", ".settings-save-state"],
  ["settings-navigation", "default", ".settings-nav"],
  ["settings-search", "matches", ".settings-search"],
  ["settings-section", "unsaved", ".settings-section"],
  ["foundations-forms-field", "invalid", ".ui-field"],
];

async function scan(page: Page, include: string) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({page}).include(include).withTags(TAGS).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}

for (const [id, story, include] of STORIES) {
  test(`Settings ${id}/${story} has no WCAG 2.2 AA violations`, async ({page}) => {
    await page.goto(`/iframe.html?id=${id}--${story}&viewMode=story`);
    await expect(page.locator(include).first()).toBeVisible();
    const results = await scan(page, include);
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test("keyboard: Settings contents rail is operable with arrows and shows a visible focus ring", async ({page}) => {
  await page.goto("/iframe.html?id=settings-navigation--default&viewMode=story");
  const first = page.getByRole("tab").first();
  await first.focus();
  const outline = await first.evaluate(el => {
    const style = getComputedStyle(el);
    return {width: parseFloat(style.outlineWidth), style: style.outlineStyle};
  });
  expect(outline.style).not.toBe("none");
  expect(outline.width).toBeGreaterThanOrEqual(2);
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("tab").nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tab").nth(1)).toBeFocused();
});

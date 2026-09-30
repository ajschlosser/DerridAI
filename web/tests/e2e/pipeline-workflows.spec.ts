/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function scan(page: Page, include: string) {
  const results = await new AxeBuilder({ page }).include(include).withTags(TAGS).analyze();
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
}

const stories = [
  ["pipelines-workflow-contract--reviewer-evidence", ".workflow-contract"],
  ["pipelines-strategy-catalog--all-strategies", ".strategy-catalog"],
  ["pipelines-definition-browser--evidence-workflow", ".pipeline-browser"],
  ["pipelines-version-editor-panel--inspect-only-stage", ".editor-card"],
  ["pipelines-definition-detail--assigned", ".pipeline-detail"],
  ["pipelines-operational-health--populated", ".metrics-workspace"],
  ["pipelines-execution-history--default", ".trace-workspace"],
] as const;

for (const scheme of ["light", "dark"] as const) {
  for (const [id, root] of stories) {
    test(`${id} has no WCAG 2.2 AA violations (${scheme})`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto(`/iframe.html?id=${id}&viewMode=story`);
      await page.evaluate((value) => {
        document.documentElement.dataset.colorScheme = value;
      }, scheme);
      await expect(page.locator(root).first()).toBeVisible();
      await scan(page, root);
    });
  }
}

test("strategy search and technical details work from the keyboard", async ({ page }) => {
  await page.goto("/iframe.html?id=pipelines-strategy-catalog--all-strategies&viewMode=story");
  const search = page.getByRole("searchbox", { name: "Search strategies" });
  await search.focus();
  await page.keyboard.type("cross-encoder");
  const card = page.locator('[data-strategy="rerank.cross_encoder"]');
  await expect(card).toBeVisible();
  await expect(card).toContainText("Relevance ranking only — does not establish support");

  const usage = card.locator(".strategy-usage summary");
  await usage.focus();
  await page.keyboard.press("Enter");
  await expect(
    card.getByRole("button", { name: /Research — current production chain/ }),
  ).toBeVisible();
});

test("workflow filter options expose their pressed state", async ({ page }) => {
  await page.goto("/iframe.html?id=pipelines-definition-browser--evidence-workflow&viewMode=story");
  const group = page.getByRole("group", { name: "Used for" });
  await expect(group.getByRole("button", { name: /Evidence/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator(".pipeline-choice")).toHaveCount(2);
});

test("clone editor explains disabled operations", async ({ page }) => {
  await page.goto(
    "/iframe.html?id=pipelines-version-editor-panel--inspect-only-stage&viewMode=story",
  );
  await expect(page.locator(".purpose-help")).toContainText(
    "remains a Reviewer evidence suggestion pipeline",
  );
  await expect(page.locator(".stage-fit-note").first()).toContainText("stays inspect-only");
  await page.getByLabel(/Show operations this workflow cannot run/).check();
  await expect(page.locator('option[value="llm.generate_answer"]').first()).toHaveAttribute(
    "disabled",
    "",
  );
});

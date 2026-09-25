import { expect, test } from "@playwright/test";
import { runAxe } from "./support/axe";

for (const story of ["database-required", "database-required-without-access"]) {
  test(`database-required empty state (${story}) is announced and WCAG 2.0 AA clean`, async ({
    page,
  }) => {
    await page.goto(`/iframe.html?id=foundations-feedback-empty-state--${story}&viewMode=story`);
    const state = page.locator(".accessible-empty-state");
    await expect(state).toBeVisible();
    await expect(state).toHaveAttribute("role", "status");
    await expect(state.getByRole("heading", { level: 2 })).toContainText("corpus database");
    const button = state.getByRole("button");
    await expect(button).toHaveCount(story === "database-required" ? 1 : 0);
    const results = await runAxe(page, (builder) =>
      builder.include(".accessible-empty-state").withTags(["wcag2a", "wcag2aa"]),
    );
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

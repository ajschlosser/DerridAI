/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockBackend } from "./support/mock-backend";
import { scenarios } from "./support/view-scenarios";

// The Vue views (Languages, Response Library, Record, Settings, Compare) have no Storybook stories, so
// they are rendered here in the real app against a mock backend, in light and in dark, and scanned
// with axe for WCAG 2.0 to 2.2 A and AA. The app is served from the production build (see the second
// webServer in playwright.config.ts).
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function openScenario(page: Page, scenario: (typeof scenarios)[number]) {
  await mockBackend(page, { role: scenario.role, fixtures: scenario.fixtures });
  await page.goto(APP + scenario.path);
  await scenario.steps?.(page);
  await expect(scenario.ready(page), `${scenario.id} did not reach its state`).toBeVisible();
}

for (const scheme of ["light", "dark"] as const) {
  for (const scenario of scenarios) {
    test(`${scenario.id} is WCAG 2.2 AA clean in ${scheme} mode`, async ({ browser }, testInfo) => {
      test.skip(
        testInfo.project.name !== "chromium-desktop",
        "The view scan runs once, at desktop width.",
      );
      const context = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        colorScheme: scheme,
        reducedMotion: "reduce",
      });
      // The app reads the saved preference, so set it as a person would.
      await context.addInitScript(
        (value) => localStorage.setItem("derridai.ui.scheme", value),
        scheme,
      );
      const page = await context.newPage();
      await openScenario(page, scenario);
      await expect(page.locator("html")).toHaveAttribute("data-color-scheme", scheme);
      const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
      expect(
        violations,
        JSON.stringify(
          violations.map((v) => ({
            rule: v.id,
            nodes: v.nodes
              .slice(0, 3)
              .map((n) => ({ target: n.target.join(" "), why: n.any[0]?.message })),
          })),
          null,
          2,
        ),
      ).toEqual([]);
      await context.close();
    });
  }
}

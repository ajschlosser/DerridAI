/* Copyright 2026 Aaron John Schlosser, PhD. */
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

/**
 * Runs axe on a page, waiting out the run Storybook's a11y addon starts on its own when a story renders.
 * Two runs at once make axe throw "Axe is already running", which made scans flaky.
 */
export async function runAxe(
  page: Page,
  configure: (builder: AxeBuilder) => AxeBuilder = (builder) => builder,
) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await configure(new AxeBuilder({ page })).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}

/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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

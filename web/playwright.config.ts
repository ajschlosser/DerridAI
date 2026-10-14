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

import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const storybookPort = process.env.STORYBOOK_PORT || "6006";
const appPort = process.env.APP_PORT || "5199";
const isCI = Boolean(process.env.CI);

// The suites run against the built Storybook, as CI does. The dev server compiles each story on
// first request, so under parallel workers a story could miss the assertion timeout.
if (!existsSync(resolve(process.cwd(), "storybook-static", "index.json"))) {
  throw new Error("storybook-static is missing; run `npm run build-storybook` first.");
}

export default defineConfig({
  testDir: "./tests/e2e",
  testIgnore: [
    "**/legacy-dom-baseline.spec.ts",
    "**/corpus-builder-theme-sweep.spec.ts",
    "**/static-site-export.spec.ts",
  ],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  workers: 2,
  retries: 0,
  reporter: isCI ? "github" : "list",
  use: {
    baseURL: `http://127.0.0.1:${storybookPort}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: [
    {
      command: `node scripts/serve-static.mjs storybook-static 127.0.0.1 ${storybookPort}`,
      url: `http://127.0.0.1:${storybookPort}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      // The real app from the production build (run `npm run build` first). Its /api/ calls are
      // answered by the mock backend in tests/e2e/support, so no API is needed.
      command: `npx vite preview --host 127.0.0.1 --port ${appPort} --strictPort`,
      url: `http://127.0.0.1:${appPort}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});

/* Copyright 2026 Aaron John Schlosser, PhD. */
import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const storybookPort = process.env.STORYBOOK_PORT || "6006";
const isCI = Boolean(process.env.CI);

// The suites run against the built Storybook, as CI does. The dev server compiles each story on
// first request, so under parallel workers a story could miss the assertion timeout.
if (!existsSync(resolve(process.cwd(), "storybook-static", "index.json"))) {
  throw new Error("storybook-static is missing; run `npm run build-storybook` first.");
}

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "corpus-builder-theme-sweep.spec.ts",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  workers: 4,
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
  webServer: {
    command: `node scripts/serve-static.mjs storybook-static 127.0.0.1 ${storybookPort}`,
    url: `http://127.0.0.1:${storybookPort}`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});

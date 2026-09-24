/* Copyright 2026 Aaron John Schlosser, PhD. */
import { defineConfig, devices } from "@playwright/test";

const storybookPort = process.env.STORYBOOK_PORT || "6006";
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "corpus-builder-theme-sweep.spec.ts",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  workers: isCI ? 4 : undefined,
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
    command: isCI
      ? `node scripts/serve-static.mjs storybook-static 127.0.0.1 ${storybookPort}`
      : `npm run storybook -- --ci --no-open -p ${storybookPort}`,
    url: `http://127.0.0.1:${storybookPort}`,
    reuseExistingServer: !isCI && !process.env.STORYBOOK_PORT,
    timeout: 60_000,
  },
});

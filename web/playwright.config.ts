import { defineConfig, devices } from "@playwright/test";

const storybookPort = process.env.STORYBOOK_PORT || "6006";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${storybookPort}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium-desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "chromium-laptop", use: { ...devices["Desktop Chrome"], viewport: { width: 1024, height: 768 } } },
  ],
  webServer: {
    command: `npm run storybook -- --ci --no-open -p ${storybookPort}`,
    url: `http://127.0.0.1:${storybookPort}`,
    reuseExistingServer: !process.env.CI && !process.env.STORYBOOK_PORT,
    timeout: 120_000,
  },
});

import { defineConfig, devices } from "@playwright/test";

// Runs only the legacy DOM baseline against the production build, without Storybook.
// Usage: npm run build && npm run test:e2e:legacy
const appPort = process.env.APP_PORT || "5199";
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "legacy-dom-baseline.spec.ts",
  timeout: 30_000,
  fullyParallel: true,
  workers: isCI ? 2 : undefined,
  retries: 0,
  snapshotPathTemplate: "{snapshotDir}/{testFilePath}-snapshots/{arg}{ext}",
  reporter: isCI ? "github" : "list",
  use: {
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
    command: `npx vite preview --host 127.0.0.1 --port ${appPort} --strictPort`,
    url: `http://127.0.0.1:${appPort}`,
    reuseExistingServer: !isCI && !process.env.APP_PORT,
    timeout: 60_000,
  },
});

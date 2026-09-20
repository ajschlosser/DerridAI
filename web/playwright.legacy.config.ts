import { defineConfig, devices } from "@playwright/test";

// Runs only the legacy DOM baseline against the production build, without Storybook.
// Usage: npm run build && npx playwright test -c playwright.legacy.config.ts
const appPort = process.env.APP_PORT || "5199";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "legacy-dom-baseline.spec.ts",
  timeout: 30_000,
  fullyParallel: true,
  reporter: "list",
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: {
    command: `npx vite preview --host 127.0.0.1 --port ${appPort} --strictPort`,
    url: `http://127.0.0.1:${appPort}`,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});

import { defineConfig, devices } from "@playwright/test";

const storybookPort = process.env.STORYBOOK_PORT || "6006";
const appPort = process.env.APP_PORT || "5199";
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/e2e",
  testIgnore: ["**/legacy-dom-baseline.spec.ts", "**/corpus-builder-theme-sweep.spec.ts"],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  workers: isCI ? 2 : undefined,
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
      command: isCI
        ? `node scripts/serve-static.mjs storybook-static 127.0.0.1 ${storybookPort}`
        : `npm run storybook -- --ci --no-open -p ${storybookPort}`,
      url: `http://127.0.0.1:${storybookPort}`,
      reuseExistingServer: !isCI && !process.env.STORYBOOK_PORT,
      timeout: 60_000,
    },
    {
      // The real app from the production build (run `npm run build` first). Its /api/ calls are
      // answered by the mock backend in tests/e2e/support, so no API is needed.
      command: `npx vite preview --host 127.0.0.1 --port ${appPort} --strictPort`,
      url: `http://127.0.0.1:${appPort}`,
      reuseExistingServer: !isCI && !process.env.APP_PORT,
      timeout: 60_000,
    },
  ],
});

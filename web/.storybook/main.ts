// Copyright 2026 Aaron John Schlosser, PhD.
import type { StorybookConfig } from "@storybook/vue3-vite";
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const webRoot = join(root, "..");
const pkg = JSON.parse(readFileSync(join(webRoot, "package.json"), "utf8")) as { version: string };
function gitCommit(): string {
  const fromEnv = String(process.env.GIT_COMMIT || process.env.SOURCE_COMMIT || "").trim();
  if (fromEnv) return fromEnv.split(/\s+/)[0].slice(0, 40);
  try {
    return execSync("git rev-parse --short HEAD", { encoding: "utf8", cwd: webRoot }).trim();
  } catch {
    return "";
  }
}

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(js|ts)"],
  addons: ["@storybook/addon-a11y"],
  framework: {
    name: "@storybook/vue3-vite",
    options: {},
  },
  async viteFinal(config) {
    config.define = {
      ...config.define,
      __APP_VERSION__: JSON.stringify(pkg.version),
      __APP_GIT_COMMIT__: JSON.stringify(gitCommit()),
    };
    return config;
  },
};

export default config;

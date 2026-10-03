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

import type { StorybookConfig } from "@storybook/vue3-vite";
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const webRoot = join(root, "..");
const pkg = JSON.parse(readFileSync(join(webRoot, "package.json"), "utf8")) as {
  version: string;
  codename: string;
};
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
      __APP_CODENAME__: JSON.stringify(pkg.codename),
      __APP_GIT_COMMIT__: JSON.stringify(gitCommit()),
    };
    return config;
  },
};

export default config;

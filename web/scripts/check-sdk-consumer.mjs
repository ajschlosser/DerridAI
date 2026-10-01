// Copyright 2026 Aaron John Schlosser, PhD.
import { execFileSync } from "node:child_process";
import {
  cpSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixtureRoot = join(webRoot, "tests", "fixtures", "sdk-consumer");
const workspace = mkdtempSync(join(tmpdir(), "derridai-sdk-consumer-"));

function run(command, args, cwd) {
  execFileSync(command, args, {
    cwd,
    stdio: "inherit",
    env: { ...process.env, npm_config_audit: "false", npm_config_fund: "false" },
  });
}

function output(command, args, cwd) {
  return execFileSync(command, args, {
    cwd,
    encoding: "utf8",
    env: { ...process.env, npm_config_audit: "false", npm_config_fund: "false" },
  });
}

try {
  const packDir = join(workspace, "pack");
  const consumerDir = join(workspace, "consumer");
  mkdirSync(packDir);
  cpSync(fixtureRoot, consumerDir, { recursive: true });

  run("npm", ["pack", "./sdk", "--pack-destination", packDir], webRoot);
  const tarballs = readdirSync(packDir).filter((name) => name.endsWith(".tgz"));
  if (tarballs.length !== 1) {
    throw new Error(`Expected one SDK tarball, found ${tarballs.length}.`);
  }

  const tarball = join(packDir, tarballs[0]);
  const packedFiles = output("tar", ["-tzf", tarball], webRoot)
    .trim()
    .split("\n")
    .filter(Boolean);
  const unexpected = packedFiles.filter(
    (path) =>
      path !== "package/package.json" &&
      path !== "package/README.md" &&
      path !== "package/CHANGELOG.md" &&
      !path.startsWith("package/dist/"),
  );
  if (unexpected.length) {
    throw new Error(`Unexpected files in SDK tarball: ${unexpected.join(", ")}`);
  }
  if (!packedFiles.includes("package/dist/index.js") || !packedFiles.includes("package/dist/index.d.ts")) {
    throw new Error("SDK tarball is missing its JavaScript or TypeScript declaration entry point.");
  }

  const packagePath = join(consumerDir, "package.json");
  const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
  packageJson.dependencies = {
    "@derridai/sdk": `file:${tarball}`,
  };
  writeFileSync(packagePath, `${JSON.stringify(packageJson, null, 2)}\n`);

  run("npm", ["install", "--ignore-scripts", "--no-audit", "--no-fund"], consumerDir);
  run(join(webRoot, "node_modules", ".bin", "tsc"), ["-p", "tsconfig.json"], consumerDir);
  run("node", ["dist-ts/index.js"], consumerDir);
  run(join(webRoot, "node_modules", ".bin", "vite"), ["build"], consumerDir);
} finally {
  rmSync(workspace, { recursive: true, force: true });
}

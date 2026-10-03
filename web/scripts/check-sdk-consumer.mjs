// Copyright 2026 Aaron John Schlosser, PhD.
import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixtureRoot = join(webRoot, "tests", "fixtures", "sdk-consumer");
const workspace = mkdtempSync(join(tmpdir(), "derridai-sdk-consumer-"));

const npmCli = process.env.npm_execpath;
const npmCommand = npmCli ? process.execPath : "npm";
const npmArgs = (args) => (npmCli ? [npmCli, ...args] : args);

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

  const packed = JSON.parse(
    output(
      npmCommand,
      npmArgs(["pack", "./sdk", "--json", "--pack-destination", packDir]),
      webRoot,
    ),
  );
  if (!Array.isArray(packed) || packed.length !== 1 || !packed[0]?.filename) {
    throw new Error("npm pack did not return exactly one SDK package.");
  }

  const tarball = join(packDir, packed[0].filename);
  const packedFiles = (packed[0].files ?? []).map((item) => String(item.path));
  const unexpected = packedFiles.filter(
    (path) =>
      path !== "package.json" &&
      path !== "README.md" &&
      path !== "CHANGELOG.md" &&
      !path.startsWith("dist/"),
  );
  if (unexpected.length) {
    throw new Error(`Unexpected files in SDK tarball: ${unexpected.join(", ")}`);
  }
  if (!packedFiles.includes("dist/index.js") || !packedFiles.includes("dist/index.d.ts")) {
    throw new Error("SDK tarball is missing its JavaScript or TypeScript declaration entry point.");
  }

  const packagePath = join(consumerDir, "package.json");
  const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
  packageJson.dependencies = {
    "@derridai/sdk": `file:${tarball}`,
  };
  writeFileSync(packagePath, `${JSON.stringify(packageJson, null, 2)}\n`);

  run(npmCommand, npmArgs(["install", "--ignore-scripts", "--no-audit", "--no-fund"]), consumerDir);
  run(
    process.execPath,
    [join(webRoot, "node_modules", "typescript", "bin", "tsc"), "-p", "tsconfig.json"],
    consumerDir,
  );
  run(process.execPath, ["dist-ts/index.js"], consumerDir);
  run(
    process.execPath,
    [join(webRoot, "node_modules", "vite", "bin", "vite.js"), "build"],
    consumerDir,
  );
} finally {
  rmSync(workspace, { recursive: true, force: true });
}

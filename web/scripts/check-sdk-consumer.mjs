// Copyright 2026 Aaron John Schlosser, PhD.
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const fixture = resolve(webRoot, "tests/fixtures/sdk-consumer");
const temp = mkdtempSync(join(tmpdir(), "derridai-sdk-consumer-"));

function run(command, args, options = {}) {
  execFileSync(command, args, {
    cwd: webRoot,
    stdio: "inherit",
    ...options,
  });
}

try {
  const packJson = execFileSync(
    "npm",
    ["pack", "./sdk", "--json", "--pack-destination", temp],
    { cwd: webRoot, encoding: "utf8" },
  );
  const packed = JSON.parse(packJson);
  const tarball = resolve(temp, packed[0].filename);

  run("npm", [
    "install",
    "--prefix",
    fixture,
    "--no-package-lock",
    "--ignore-scripts",
    "--no-audit",
    "--no-fund",
    "--no-save",
    tarball,
  ]);

  run(resolve(webRoot, "node_modules/.bin/tsc"), ["--noEmit", "-p", resolve(fixture, "tsconfig.json")]);
  run(resolve(webRoot, "node_modules/.bin/vite"), [
    "build",
    fixture,
    "--outDir",
    resolve(temp, "dist"),
    "--emptyOutDir",
  ]);
} finally {
  rmSync(resolve(fixture, "node_modules"), { recursive: true, force: true });
  rmSync(temp, { recursive: true, force: true });
}

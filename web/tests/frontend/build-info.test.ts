// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { APP_GIT_COMMIT, APP_VERSION, COPYRIGHT_YEAR, appVersionLabel } from "../../src/buildInfo";
import pkg from "../../package.json";

describe("buildInfo", () => {
  it("uses the package version", () => {
    expect(APP_VERSION).toBe(pkg.version);
  });

  it("pins the UI copyright year", () => {
    expect(COPYRIGHT_YEAR).toBe("2026");
  });

  it("puts the commit in parentheses when present", () => {
    expect(appVersionLabel("1.2.3", "abc1234")).toBe("1.2.3 (abc1234)");
    expect(appVersionLabel("1.2.3", "")).toBe("1.2.3");
  });

  it("exposes a git commit string from the build", () => {
    expect(typeof APP_GIT_COMMIT).toBe("string");
  });
});

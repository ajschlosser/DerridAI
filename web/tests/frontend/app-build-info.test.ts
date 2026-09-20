/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AppBuildInfo from "../../src/components/AppBuildInfo.vue";
import pkg from "../../package.json";

describe("AppBuildInfo", () => {
  it("shows the copyright holder and package version", () => {
    const text = mount(AppBuildInfo).text();
    expect(text).toContain("The New England Transcendental Club of California");
    expect(text).toContain(`DerridAI ${pkg.version}`);
    expect(text).toContain("© 2026");
  });

  it("hides the git commit unless asked", () => {
    expect(mount(AppBuildInfo).text()).not.toContain("Build vitest");
    expect(mount(AppBuildInfo, {props: {showCommit: true}}).text()).toContain("Build vitest");
  });

  it("can omit copyright for compact version-only chrome", () => {
    const text = mount(AppBuildInfo, {props: {showCopyright: false}}).text();
    expect(text).toContain(`DerridAI ${pkg.version}`);
    expect(text).not.toContain("The New England Transcendental Club of California");
  });
});

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import CommandSearch from "../../src/components/CommandSearch.vue";
import { jobProgressText } from "../../src/runtime/runtime.js";

describe("CommandSearch shortcut hint", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("advertises the modifier key for the current platform", () => {
    vi.stubGlobal("navigator", { platform: "Linux x86_64", userAgent: "" });
    expect(mount(CommandSearch).get("kbd").text()).toBe("Ctrl K");
    vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "" });
    expect(mount(CommandSearch).get("kbd").text()).toBe("⌘K");
  });

  it("lets a caller override the hint", () => {
    expect(mount(CommandSearch, { props: { shortcut: "/" } }).get("kbd").text()).toBe("/");
  });
});

describe("jobProgressText", () => {
  it("shows only a percentage for corpus builds, whose count is synthetic", () => {
    const text = jobProgressText({ type: "pdf_corpus", completed: 133, total: 307 });
    expect(text).toBe("43% overall");
    expect(text).not.toContain("307");
  });

  it("says a finished build is ready for review instead of reporting its internal percentage", () => {
    expect(jobProgressText({ type: "pdf_corpus", status: "completed", completed: 277, total: 307 })).toBe("Build complete · ready for review");
    expect(jobProgressText({ type: "pdf_corpus", status: "running", completed: 133, total: 307 })).toBe("43% overall");
  });

  it("keeps real counts for other operations", () => {
    expect(jobProgressText({ type: "upsert", completed: 5, total: 10 })).toBe("5/10 (50%)");
    expect(jobProgressText({ type: "upsert", completed: 5, total: 10 }, "of")).toBe("5 of 10 (50%)");
    expect(jobProgressText({ type: "llm", completed: 0, total: 0 })).toBe("0/0 (0%)");
  });
});

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

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import CommandSearch from "../../src/components/CommandSearch.vue";
import "../../src/domain/appBootstrap";
import { operationPresenters } from "../../src/domain/sharedOperationPresenters";

const { jobProgressText } = operationPresenters;

describe("CommandSearch shortcut hint", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("advertises the modifier key for the current platform", () => {
    vi.stubGlobal("navigator", { platform: "Linux x86_64", userAgent: "" });
    expect(mount(CommandSearch).get("kbd").text()).toBe("Ctrl K");
    vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "" });
    expect(mount(CommandSearch).get("kbd").text()).toBe("⌘K");
  });

  it("lets a caller override the hint", () => {
    expect(
      mount(CommandSearch, { props: { shortcut: "/" } })
        .get("kbd")
        .text(),
    ).toBe("/");
  });
});

describe("jobProgressText", () => {
  it("shows only a percentage for corpus builds, whose count is synthetic", () => {
    const text = jobProgressText({ type: "pdf_corpus", completed: 133, total: 307 });
    expect(text).toBe("43% overall");
    expect(text).not.toContain("307");
  });

  it("says a finished build is ready for review instead of reporting its internal percentage", () => {
    expect(
      jobProgressText({ type: "pdf_corpus", status: "completed", completed: 277, total: 307 }),
    ).toBe("Build complete · ready for review");
    expect(
      jobProgressText({ type: "pdf_corpus", status: "running", completed: 133, total: 307 }),
    ).toBe("43% overall");
  });

  it("keeps real counts for other operations", () => {
    expect(jobProgressText({ type: "upsert", completed: 5, total: 10 })).toBe("5/10 (50%)");
    expect(jobProgressText({ type: "upsert", completed: 5, total: 10 }, "of")).toBe(
      "5 of 10 (50%)",
    );
    expect(jobProgressText({ type: "llm", completed: 0, total: 0 })).toBe("0/0 (0%)");
  });
});

/*
 * This file is part of DerridAI, a cELF-compliant research workspace.
 * Copyright © 2026 Aaron John Schlosser, PhD.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { describe, expect, it } from "vitest";
import {
  formatSourcePageSelection,
  parseSourcePageSelection,
} from "../../src/domain/sourcePageScope";

describe("source page scope", () => {
  it("accepts ranges and individual pages and normalizes duplicates", () => {
    expect(parseSourcePageSelection("1-3, 7, 10-12, 7", 20)).toEqual({
      pages: [1, 2, 3, 7, 10, 11, 12],
      error: "",
    });
  });

  it("treats an empty value as the complete source", () => {
    expect(parseSourcePageSelection("", 20)).toEqual({ pages: [], error: "" });
  });

  it("rejects malformed, reversed, and out-of-range selections", () => {
    expect(parseSourcePageSelection("1-x", 20).error).toBeTruthy();
    expect(parseSourcePageSelection("1,,3", 20).error).toBeTruthy();
    expect(parseSourcePageSelection("9-4", 20).error).toBeTruthy();
    expect(parseSourcePageSelection("21", 20).error).toBeTruthy();
  });

  it("formats contiguous selections compactly", () => {
    expect(formatSourcePageSelection([1, 2, 3, 7, 10, 11, 12])).toBe("1-3, 7, 10-12");
  });
});

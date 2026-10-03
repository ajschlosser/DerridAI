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

import { afterEach, describe, expect, it, vi } from "vitest";
import { forwardVerticalWheelToDocument } from "../../src/composables/forwardVerticalWheelToDocument";

function wheel(deltaY: number, path: EventTarget[]) {
  const event = new WheelEvent("wheel", { deltaY, bubbles: true });
  Object.defineProperty(event, "composedPath", { value: () => path });
  return event;
}

describe("forwardVerticalWheelToDocument", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.documentElement.scrollTop = 0;
  });

  it("moves the document when an inner auto overflow node cannot scroll", () => {
    const trap = document.createElement("div");
    Object.defineProperties(trap, {
      scrollHeight: { value: 200 },
      clientHeight: { value: 200 },
      scrollTop: { value: 0, writable: true },
    });
    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      overflowY: "auto",
    } as CSSStyleDeclaration);
    document.documentElement.scrollTop = 12;
    forwardVerticalWheelToDocument(wheel(80, [trap, document.documentElement]));
    expect(document.documentElement.scrollTop).toBe(92);
  });

  it("leaves the document alone when the inner node can still scroll", () => {
    const scroller = document.createElement("div");
    Object.defineProperties(scroller, {
      scrollHeight: { value: 400 },
      clientHeight: { value: 200 },
      scrollTop: { value: 0, writable: true },
    });
    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      overflowY: "auto",
    } as CSSStyleDeclaration);
    document.documentElement.scrollTop = 12;
    forwardVerticalWheelToDocument(wheel(80, [scroller, document.documentElement]));
    expect(document.documentElement.scrollTop).toBe(12);
  });
});

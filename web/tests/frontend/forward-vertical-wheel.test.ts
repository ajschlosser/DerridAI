/* Copyright 2026 Aaron John Schlosser, PhD. */
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

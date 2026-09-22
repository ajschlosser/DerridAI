/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createOperationDock } from "../../src/domain/operationDock";
import { fitDockInViewport } from "../../src/domain/operationsDock";

function setup(html: string, state: Record<string, unknown> = {}) {
  document.body.innerHTML = `<div id="operationProgressStack" data-tone="">
    <span id="operationStackCount"></span><button id="operationStackClearFinished"></button>${html}</div>`;
  const deps = new Proxy(
    {
      state: { jobs: [], operationToastsMinimized: true, ...state },
      tr: (_key: string, fallback: string) => fallback,
      trf: (_key: string, fallback: string, values: Record<string, unknown> = {}) =>
        fallback.replace(/\{(\w+)\}/g, (_m, name) => String(values[name])),
    } as Record<string, unknown>,
    { get: (target, name: string) => target[name] ?? vi.fn() },
  );
  return createOperationDock(deps as never);
}

describe("operation dock summary", () => {
  it("counts the failed cards when every card has failed", () => {
    const dock = setup(
      '<div class="operation-progress failed"></div><div class="operation-progress failed"></div>',
    );
    dock.updateOperationStackCount();
    expect(document.querySelector("#operationStackCount")?.textContent).toBe("2 failed");
  });
});

describe("operation dock placement", () => {
  it("slides an expanded dock back on screen when it would overflow the right or bottom edge", () => {
    const viewport = { width: 1200, height: 800 };
    // Minimized pill left near the bottom-right corner, then expanded to 380 x 500.
    const fit = fitDockInViewport({ left: 1000, top: 740 }, { width: 380, height: 500 }, viewport);
    expect(fit.left + 380).toBeLessThanOrEqual(viewport.width - 8);
    expect(fit.top + 500).toBeLessThanOrEqual(viewport.height - 8);
    expect(fit.left).toBe(812);
    expect(fit.top).toBe(292);
    expect(fit.maxHeight).toBe(500);
  });

  it("keeps an anchor that already fits and never goes above or left of the margin", () => {
    const viewport = { width: 1200, height: 800 };
    expect(fitDockInViewport({ left: 40, top: 60 }, { width: 380, height: 300 }, viewport)).toEqual(
      {
        left: 40,
        top: 60,
        maxHeight: 732,
      },
    );
    const tall = fitDockInViewport({ left: -50, top: 700 }, { width: 380, height: 2000 }, viewport);
    expect(tall.left).toBe(8);
    expect(tall.top).toBe(8);
  });

  it("repositions the dock on expand without forgetting where the user left it", () => {
    const state = { operationStackPosition: { left: 1000, top: 740 } };
    const dock = setup('<div class="operation-progress"></div>', state);
    const stack = document.querySelector<HTMLElement>("#operationProgressStack")!;
    Object.defineProperty(window, "innerWidth", { value: 1200, configurable: true });
    Object.defineProperty(window, "innerHeight", { value: 800, configurable: true });
    stack.getBoundingClientRect = () => ({ width: 380, height: 500 }) as DOMRect;
    dock.setOperationDockMinimized(false);
    expect(stack.style.left).toBe("812px");
    expect(stack.style.top).toBe("292px");
    expect(state.operationStackPosition).toEqual({ left: 1000, top: 740 });
  });
});

/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createOperationDock } from "../../src/domain/operationDock";

function setup(html: string) {
  document.body.innerHTML = `<div id="operationProgressStack" data-tone="">
    <span id="operationStackCount"></span><button id="operationStackClearFinished"></button>${html}</div>`;
  const deps = new Proxy(
    {
      state: { jobs: [], operationToastsMinimized: true },
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

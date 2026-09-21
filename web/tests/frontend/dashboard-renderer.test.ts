/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createDashboardRenderer } from "../../src/domain/dashboardRenderer";

// The dashboard's markup is covered by the legacy baseline's home scenarios; this pins the latest-annotation click.
describe("dashboard latest annotation", () => {
  it("opens the shared annotation's record in its own store", () => {
    const openAnnotationsWorkspaceRecord = vi.fn();
    const deps = new Proxy(
      { state: {}, openAnnotationsWorkspaceRecord } as Record<string, unknown>,
      { get: (target, name: string) => target[name] ?? vi.fn() },
    );
    createDashboardRenderer(deps as never).openSharedAnnotationRecord("derrida", "rec-7");
    expect(openAnnotationsWorkspaceRecord).toHaveBeenCalledWith({
      server: true,
      source: "derrida",
      record_id: "rec-7",
    });
  });
});

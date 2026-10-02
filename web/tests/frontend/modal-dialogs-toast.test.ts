/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createModalDialogs } from "../../src/domain/modalDialogs";

describe("copyJsonToClipboard", () => {
  it("announces the copy through a translatable key rather than English text", async () => {
    const writeText = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const toast = vi.fn();
    const trf = vi.fn((key: string, values: Record<string, unknown>) => `${key}:${values.label}`);
    const { copyJsonToClipboard } = createModalDialogs({ state: {}, toast, trf } as never);

    await copyJsonToClipboard({ a: 1 }, "fiche");

    expect(writeText).toHaveBeenCalledWith(JSON.stringify({ a: 1 }, null, 2));
    expect(toast).toHaveBeenCalledWith("runtime.toast.json_copied:fiche");
    vi.unstubAllGlobals();
  });
});

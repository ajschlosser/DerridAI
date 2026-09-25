/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { applyProfileFieldValues, mergeSavedProfile } from "../../src/domain/providerBulkFields";
import type { ProviderProfile } from "../../src/api/system";

const ollama = {
  id: "o1",
  name: "Local",
  type: "ollama",
  num_ctx: 4096,
  temperature: 0,
} as ProviderProfile;
const openai = {
  id: "p1",
  name: "Cloud",
  type: "openai",
  num_predict: 512,
  temperature: 0.2,
} as ProviderProfile;

describe("provider bulk fields", () => {
  it("merges one saved profile without rewriting the others", () => {
    const next = mergeSavedProfile([ollama, openai], { ...openai, temperature: 0.7 });
    expect(next[0].temperature).toBe(0);
    expect(next[1].temperature).toBe(0.7);
  });

  it("applies shared values to every selected profile and skips type-specific fields", () => {
    const next = applyProfileFieldValues([ollama, openai], ["o1", "p1"], {
      temperature: 0.4,
      num_ctx: 8192,
      num_predict: 2048,
    });
    expect(next[0]).toMatchObject({ temperature: 0.4, num_ctx: 8192, num_predict: 2048 });
    expect(next[1]).toMatchObject({ temperature: 0.4, num_predict: 2048 });
    expect(next[1].num_ctx).toBeUndefined();
  });
});

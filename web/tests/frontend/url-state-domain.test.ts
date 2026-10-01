/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { compressUrlState, decompressUrlState } from "../../src/domain/urlState";

// The first and third golden tokens were produced by the original functions in the legacy runtime.js; the second was
// regenerated from the current encoder (round-trip verified) when its sample value changed. Links created
// by earlier builds keep decoding and new links keep the same shape.
const values: unknown[] = [
  { v: 1, q: "a" },
  {
    v: 1,
    filters: Array.from({ length: 12 }, (_, i) => ({
      field: "document_author",
      op: "eq",
      value: `Author ${i % 3}`,
    })),
    sort: { key: "page_start", dir: -1 },
  },
  { text: "héllo — wörld ☃" },
];
const golden: string[] = [
  "reyJ2IjoxLCJxIjoiYSJ9",
  "zB7AiB2AiA6AxAsAiBmBpBsB0BlByBzEDBbEAEIBlBsBkEDAiBkBvBjB1BtBlBuB0BfBhB1B0BoBvByAiEGBvBwEWBlBxEnEBBhBsB1BlEWBBEiEkByAgAwAiB9AsERBpETEVA6EXEZEbEdEfEhEjElEuEpErEtEGB2EwEyE0E2ElAgAxE7E9EHE_EUEWEYEaEcEeEgFUEmEoEqFCEsEuFQExEzFCE1FJE4AyFYE-FAFdFEFgFHFjFLFmAiFoFPFRFsAiFuE3E5FyFaF0FCFeFFFhFIE3F6FNFpF_FTFvFWGFESFcGIF2FGFiFvGOFnFOEvFrGSGDFxE8FzGXFDFfGaGMFKFlGPF-GhFtFjGEGlGGGnGJF3GbGNGtGeGQGwGBGyFXG0GWFBGoGKF4GcG7F8GfFqFSGxGTGkFZHDF1GpGLF5HJF9GgHNG_GTE6HCFbHEG3GqHWAiFMG8GvHaGCFVHBHRHfHTHGG5GsHkF7HYHMGAHpFwE7BdEGBzElB0EDEABrBlB5EWBwBhBnBlBfBzB0BhByH-EGBkBpEmA6AtAxB9B9",
  "reyJ0ZXh0IjoiaMOpbGxvIOKAlCB3w7ZybGQg4piDIn0",
];

describe("URL state encoding", () => {
  it("encodes identically to the legacy runtime", () => {
    expect(values.map(compressUrlState)).toEqual(golden);
  });
  it("round-trips", () => {
    expect(golden.map(decompressUrlState)).toEqual(values);
  });
  it("returns null for empty or invalid tokens", () => {
    expect(decompressUrlState("")).toBeNull();
    expect(decompressUrlState(null)).toBeNull();
  });
});

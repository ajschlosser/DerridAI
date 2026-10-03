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

import { describe, expect, it } from "vitest";
import { compressUrlState, decompressUrlState } from "../../src/domain/urlState";

// The golden tokens were produced by the original functions in the legacy runtime.js, so links created
// by earlier builds keep decoding and new links keep the same shape.
const values: unknown[] = [
  { v: 1, q: "a" },
  {
    v: 1,
    filters: Array.from({ length: 12 }, (_, i) => ({
      field: "document_author",
      op: "eq",
      value: `Derrida ${i % 3}`,
    })),
    sort: { key: "page_start", dir: -1 },
  },
  { text: "héllo — wörld ☃" },
];
const golden: string[] = [
  "reyJ2IjoxLCJxIjoiYSJ9",
  "zB7AiB2AiA6AxAsAiBmBpBsB0BlByBzEDBbEAEIBlBsBkEDAiBkBvBjB1BtBlBuB0BfBhB1B0BoBvByAiEGBvBwEWBlBxEnEBBhBsB1BlEWBEEMByBpBkBhAgAwAiB9AsERBpETEVA6EXEZEbEdEfEhEjElEuEpErEtEGB2EwEyE0E2E4E6AxE9E_EHFBEUEWEYEaEcEeEgEiEkEmEoEqFEEsEuFSExEzFEE1ByE3E5AgAyFaFAFCFfFGFiFJFlFMFoFPFsFTFvAiFxFzE6E8E-F4FeFEFgFHFjFKFmFNFpAiFrFRGDFVFyFXAgFZGKFcF5GNF7FIFkFLFnAiFOFqFQEvFuGZGHF1F3GfGMFFFhGjGRF_GnGUGWGrFUFwFWF0GJFbESGyGOF8GkGSGAGpGCGsG9GaF0GdHBFdFDGzGPF9GlGTGBGXHLGFG-E6F2GeHCHSHEG1F-GmGoGVGqFtG8HbHNGIGwHgF6G0GQHkHXHJHZHqGGGbHPGLHhGiHyHWHIHnHKH3HcGvB9BdEGBzElB0EDEABrBlB5EWBwBhBnBlBfBzB0BhByILEGBkBpEmA6AtAxB9B9A",
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

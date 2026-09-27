// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { allEvidenceBlockIds } from "../../src/domain/metadataEvidence";

describe("allEvidenceBlockIds", () => {
  it("counts spans cited from other records alongside the record's own", () => {
    expect(allEvidenceBlockIds({ block_ids: ["a", "b"], external_block_ids: ["b", "z"] })).toEqual([
      "a",
      "b",
      "z",
    ]);
  });
  it("is empty without evidence", () => {
    expect(allEvidenceBlockIds(undefined)).toEqual([]);
  });
});

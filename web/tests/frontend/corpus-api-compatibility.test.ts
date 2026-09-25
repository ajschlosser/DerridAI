/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { legacyCorpusUrl } from "../../src/api/corpus/compatibility";

describe("Corpus Builder legacy route compatibility", () => {
  it("keeps PDF-named server routes behind one adapter", () => {
    expect(legacyCorpusUrl("assets")).toBe("/api/pdf/assets");
    expect(legacyCorpusUrl("/corpus-builds")).toBe("/api/pdf/corpus-builds");
  });
});

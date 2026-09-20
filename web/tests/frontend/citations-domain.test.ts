/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  fullCitation,
  inlineCitation,
  mlaAuthorName,
  mlaPageSpan,
} from "../../src/domain/citations";

describe("citations", () => {
  it("formats author names", () => {
    expect(mlaAuthorName("Jacques Derrida")).toBe("Derrida, Jacques");
    expect(mlaAuthorName("Derrida, Jacques")).toBe("Derrida, Jacques");
    expect(mlaAuthorName("Plato")).toBe("Plato");
    expect(mlaAuthorName("")).toBe("");
  });
  it("formats page spans", () => {
    expect(mlaPageSpan({ page_start: 5, page_end: 5 })).toBe("p. 5");
    expect(mlaPageSpan({ page_start: 5, page_end: 8 })).toBe("pp. 5–8");
    expect(mlaPageSpan({ page_start: 5, page_end: 8 }, { prefix: false })).toBe("5–8");
    expect(mlaPageSpan({})).toBe("");
  });
  it("builds inline citations", () => {
    expect(
      inlineCitation({
        document_author: "Jacques Derrida",
        year: 1997,
        page_start: 5,
        page_end: 8,
      }),
    ).toBe("(Derrida 1997: 5-8)");
    expect(inlineCitation({ document_author: "Derrida, Jacques" })).toBe("(Derrida)");
    expect(inlineCitation({ page_start: 3 })).toBe("(3)");
    expect(inlineCitation({ record_id: "r1" })).toBe("r1");
    expect(inlineCitation(null)).toBe("Record");
  });
  it("builds full citations", () => {
    expect(
      fullCitation({
        document_author: "Jacques Derrida",
        work: "Of Grammatology",
        translator: "G. Spivak",
        publisher: "JHU Press",
        year: 1976,
        page_start: 5,
      }),
    ).toBe("Derrida, Jacques. Of Grammatology. Translated by G. Spivak, JHU Press, 1976, p. 5.");
    expect(fullCitation({ work: "X", page_start: 2 }, { includePages: false })).toBe("X.");
    expect(fullCitation({ record_id: "r9" })).toBe("r9");
  });
});

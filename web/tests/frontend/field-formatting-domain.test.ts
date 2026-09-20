/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createFieldFormatting } from "../../src/domain/fieldFormatting";

// These behaviors were checked against the original legacy runtime.js functions across a wide input matrix.
const fields = createFieldFormatting({
  tr: (key, fallback = "") =>
    key === "field.work" ? "Œuvre" : key === "runtime.yes" ? "Oui" : fallback,
});

describe("field formatting", () => {
  it("labels fields, translating when a translation exists", () => {
    expect(fields.label("work")).toBe("Œuvre");
    expect(fields.label("document_author")).toBe("Document author");
    expect(fields.label("some_unknown_field")).toBe("Some Unknown Field");
  });
  it("displays values", () => {
    expect(fields.display(null)).toBe("—");
    expect(fields.display([])).toBe("—");
    expect(fields.display(["a", { b: 1 }])).toBe('a, {"b":1}');
    expect(fields.display(true)).toBe("Oui");
    expect(fields.display(0)).toBe("0");
  });
  it("normalizes graders' output into one shape", () => {
    const grade = fields.normalizeRagGrade({
      result: { overall_summary: "ok", strengths: ["a", ["b"]], weakness: "w" },
    });
    expect(grade).toMatchObject({ summary: "ok", strengths: ["a", "b"], weaknesses: ["w"] });
    const scored = fields.normalizeRagGrade({ scores: { faithfulness: { score: 4 } } });
    expect(scored.score("faithfulness")).toBe(4);
    expect(scored.score("missing")).toBe("—");
    expect(fields.normalizeRagGrade("just text").summary).toBe("just text");
  });
  it("parses bulk edit values by the field's existing type", () => {
    const rows = (value: unknown) => [{ record: { f: value } }];
    expect(fields.parseBulkFieldValue("f", " __NULL__ ", rows("s"))).toBeNull();
    expect(fields.parseBulkFieldValue("f", "YES", rows(true))).toBe(true);
    expect(fields.parseBulkFieldValue("f", "3", rows(1))).toBe(3);
    expect(fields.parseBulkFieldValue("f", "[1]", rows(["a"]))).toEqual([1]);
    expect(fields.parseBulkFieldValue("f", "text", rows("s"))).toBe("text");
    expect(() => fields.parseBulkFieldValue("f", "maybe", rows(true))).toThrow(
      "Enter true or false for F.",
    );
    expect(() => fields.parseBulkFieldValue("f", "x", rows(1))).toThrow("F requires a number.");
    expect(() => fields.parseBulkFieldValue("f", "{bad", rows({ a: 1 }))).toThrow(
      "F requires valid JSON",
    );
  });
  it("parses work metadata form values by the field's existing type", () => {
    const rows = (value: unknown) => [{ record: { f: value } }];
    expect(fields.parseWorkMetadataValue("f", { value: "true" }, rows(true))).toBe(true);
    expect(fields.parseWorkMetadataValue("f", { value: "" }, rows(true))).toBeNull();
    expect(fields.parseWorkMetadataValue("year", { value: " " }, rows(2001))).toBeNull();
    expect(fields.parseWorkMetadataValue("f", { value: "3" }, rows(1))).toBe(3);
    expect(() => fields.parseWorkMetadataValue("f", { value: "x" }, rows(1))).toThrow(
      "F must be numeric.",
    );
    expect(() => fields.parseWorkMetadataValue("f", { value: '{"a":1}' }, rows(["a"]))).toThrow(
      "F must be a JSON array.",
    );
    expect(fields.parseWorkMetadataValue("f", { value: "text" }, rows("s"))).toBe("text");
  });
});

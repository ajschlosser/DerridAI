/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { firstValidationRecordId } from "../../src/features/corpus-builder/domain/publicationReadiness";

describe("Corpus Builder publication readiness targeting", () => {
  it("prefers explicit validation issues with record ids", () => {
    expect(
      firstValidationRecordId({
        validation: {
          validation_issues: [{ record_id: "record-explicit" }],
          metadata_schema_errors: [{ record_id: "record-schema" }],
        },
      } as any),
    ).toBe("record-explicit");
  });

  it("falls back through structured validation families before citation errors", () => {
    expect(
      firstValidationRecordId({
        validation: {
          relationship_errors: [{ record_id: "record-relationship" }],
          citation_errors: ["record-citation"],
        },
      } as any),
    ).toBe("record-relationship");
  });

  it("uses citation errors as the final record-target fallback", () => {
    expect(
      firstValidationRecordId({
        validation: { citation_errors: ["record-citation"] },
      } as any),
    ).toBe("record-citation");
  });

  it("returns an empty target when validation has no record identity", () => {
    expect(firstValidationRecordId({ validation: {} } as any)).toBe("");
  });
});

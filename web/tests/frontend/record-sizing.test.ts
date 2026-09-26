// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { invalidRecordSizingFields } from "../../src/features/corpus-builder/domain/recordSizing";

const base = {
  preferred_record_chars: 300,
  record_length_tolerance: 30,
  long_record_chars: 400,
  absolute_record_chars: 500,
};

describe("invalidRecordSizingFields", () => {
  it("accepts small but consistent policies", () => {
    expect(invalidRecordSizingFields(base)).toEqual([]);
  });
  it("flags inconsistent limits instead of rewriting them", () => {
    expect(invalidRecordSizingFields({ ...base, long_record_chars: 320 })).toEqual([
      "long_record_chars",
    ]);
    expect(invalidRecordSizingFields({ ...base, absolute_record_chars: 350 })).toEqual([
      "absolute_record_chars",
    ]);
  });
});

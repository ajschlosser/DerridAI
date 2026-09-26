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

import {
  autoRecordSizingLimits,
  limitsAreAutomatic,
  recordSizingMinimums,
} from "../../src/features/corpus-builder/domain/recordSizing";

describe("automatic record-size limits", () => {
  it("are always valid and reproduce the defaults", () => {
    expect(autoRecordSizingLimits(1750, 200)).toEqual({
      long_record_chars: 3500,
      absolute_record_chars: 6000,
    });
    for (const [preferred, tolerance] of [
      [100, 10],
      [150, 30],
      [400, 60],
      [900, 120],
      [12000, 2000],
    ]) {
      const limits = autoRecordSizingLimits(preferred, tolerance);
      expect(
        invalidRecordSizingFields({
          preferred_record_chars: preferred,
          record_length_tolerance: tolerance,
          ...limits,
        }),
      ).toEqual([]);
    }
  });
  it("knows whether a policy follows the rule and what each limit's minimum is", () => {
    expect(
      limitsAreAutomatic({
        ...base,
        ...autoRecordSizingLimits(300, 30),
        preferred_record_chars: 300,
        record_length_tolerance: 30,
      }),
    ).toBe(true);
    expect(limitsAreAutomatic({ ...base, absolute_record_chars: 9999 })).toBe(false);
    expect(recordSizingMinimums(base)).toEqual({
      long_record_chars: 330,
      absolute_record_chars: 400,
    });
  });
});

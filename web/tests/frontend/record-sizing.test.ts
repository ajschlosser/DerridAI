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

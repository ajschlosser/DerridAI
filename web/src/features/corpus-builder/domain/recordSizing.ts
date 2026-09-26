// Copyright 2026 Aaron John Schlosser, PhD.
import type { RecordSizingPolicy } from "../../../types/corpus";

/** Mirrors PdfCorpusRecordSizing on the API; keep the two in step. */
export const RECORD_SIZING_MIN = {
  preferred_record_chars: 100,
  record_length_tolerance: 10,
  long_record_chars: 100,
  absolute_record_chars: 100,
} as const;

/** Keys of the sizing fields that currently violate the policy. Empty when valid. */
export function invalidRecordSizingFields(
  policy: RecordSizingPolicy,
): (keyof RecordSizingPolicy)[] {
  const bad = new Set<keyof RecordSizingPolicy>();
  for (const key of Object.keys(RECORD_SIZING_MIN) as (keyof typeof RECORD_SIZING_MIN)[]) {
    const value = Number(policy[key]);
    if (!Number.isFinite(value) || value < RECORD_SIZING_MIN[key]) bad.add(key);
  }
  if (
    Number(policy.long_record_chars) <
    Number(policy.preferred_record_chars) + Number(policy.record_length_tolerance)
  )
    bad.add("long_record_chars");
  if (Number(policy.absolute_record_chars) < Number(policy.long_record_chars))
    bad.add("absolute_record_chars");
  return [...bad];
}

/** Round to a tidy number: the step grows with the magnitude, so 6,125 becomes 6,000 and 350 stays 350. */
function nice(value: number): number {
  const step = value >= 2000 ? 500 : value >= 300 ? 50 : 10;
  return Math.max(step, Math.round(value / step) * step);
}

/**
 * The exception limits that follow a target automatically: a long record may run to about twice the
 * target and never past about three and a half times it. Always valid by construction.
 */
export function autoRecordSizingLimits(
  preferred: number,
  tolerance: number,
): Pick<RecordSizingPolicy, "long_record_chars" | "absolute_record_chars"> {
  const long = Math.max(preferred + tolerance, nice(preferred * 2));
  return { long_record_chars: long, absolute_record_chars: Math.max(long, nice(preferred * 3.5)) };
}

/** Do the exception limits equal what the target would give them automatically? */
export function limitsAreAutomatic(policy: RecordSizingPolicy): boolean {
  const auto = autoRecordSizingLimits(
    Number(policy.preferred_record_chars),
    Number(policy.record_length_tolerance),
  );
  return (
    Number(policy.long_record_chars) === auto.long_record_chars &&
    Number(policy.absolute_record_chars) === auto.absolute_record_chars
  );
}

/** The smallest value each limit may take right now; used to explain and to offer a one-click fix. */
export function recordSizingMinimums(policy: RecordSizingPolicy) {
  const long = Number(policy.preferred_record_chars) + Number(policy.record_length_tolerance);
  return {
    long_record_chars: long,
    absolute_record_chars: Math.max(long, Number(policy.long_record_chars)),
  };
}

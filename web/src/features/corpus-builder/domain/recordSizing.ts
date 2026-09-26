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

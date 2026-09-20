/* Copyright 2026 Aaron John Schlosser, PhD. */
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
import { TOUCHUP_CREATABLE_FIELDS, TOUCHUP_GROUPS } from "./runtimeConstants";

// Which metadata fields the LLM touch-up dialog offers for a record. Moved verbatim from the legacy runtime.

export function touchupFieldsForRecord(record: Loose): string[] {
  const known: string[] = [];
  for (const group of TOUCHUP_GROUPS) {
    for (const field of group.fields) {
      if (field in record || TOUCHUP_CREATABLE_FIELDS.has(field)) {
        if (!known.includes(field)) known.push(field);
      }
    }
  }
  for (const field of Object.keys(record)) {
    if (!known.includes(field) && field !== "text_length" && !field.startsWith("_"))
      known.push(field);
  }
  return known;
}

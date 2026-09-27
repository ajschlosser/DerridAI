// Copyright 2026 Aaron John Schlosser, PhD.
/**
 * A field's bound evidence can sit in two lists: `block_ids` are spans inside the record itself, and
 * `external_block_ids` are spans a reviewer cited from other records of the same source. The API keeps them
 * apart so audits can tell them apart; everything that asks "does this field have evidence?" or "which spans
 * should be highlighted?" must read both, which is what this helper is for.
 */
export interface FieldEvidenceIds {
  block_ids?: string[];
  external_block_ids?: string[];
}

/** Every span bound to the field, own spans first, without duplicates. */
export function allEvidenceBlockIds(info?: FieldEvidenceIds | null): string[] {
  return Array.from(
    new Set([...(info?.block_ids || []), ...(info?.external_block_ids || [])].map(String)),
  );
}

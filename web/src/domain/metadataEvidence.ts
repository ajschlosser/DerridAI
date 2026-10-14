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

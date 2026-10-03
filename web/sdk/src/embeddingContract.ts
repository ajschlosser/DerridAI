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

import type { EmbeddingContract, ProviderDescriptor } from "./types";

export interface EmbeddingContractMismatch {
  field: "model" | "revision";
  expected: string;
  actual: string;
}

export function embeddingDescriptorMismatches(
  contract: EmbeddingContract | undefined,
  descriptor: ProviderDescriptor,
): EmbeddingContractMismatch[] {
  if (!contract) return [];

  const mismatches: EmbeddingContractMismatch[] = [];
  const pairs: Array<EmbeddingContractMismatch["field"]> = ["model", "revision"];
  for (const field of pairs) {
    const expected = String(contract[field] ?? "").trim();
    const actual = String(descriptor[field] ?? "").trim();
    if (expected && actual && expected !== actual) {
      mismatches.push({ field, expected, actual });
    }
  }
  return mismatches;
}

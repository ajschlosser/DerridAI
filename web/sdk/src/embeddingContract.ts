// Copyright 2026 Aaron John Schlosser, PhD.

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

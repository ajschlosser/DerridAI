// Copyright 2026 Aaron John Schlosser, PhD.

import type { EmbeddingContract, ProviderDescriptor } from "./types";

export interface EmbeddingContractMismatch {
  expectedModel?: string;
  actualModel?: string;
  expectedRevision?: string;
  actualRevision?: string;
}

export function validateEmbeddingDescriptor(
  contract: EmbeddingContract | undefined,
  descriptor: ProviderDescriptor,
): EmbeddingContractMismatch | null {
  const expectedModel = String(contract?.model ?? "").trim();
  const actualModel = String(descriptor.model ?? "").trim();
  const expectedRevision = String(contract?.revision ?? "").trim();
  const actualRevision = String(descriptor.revision ?? "").trim();

  const mismatch: EmbeddingContractMismatch = {};
  if (expectedModel && actualModel && expectedModel !== actualModel) {
    mismatch.expectedModel = expectedModel;
    mismatch.actualModel = actualModel;
  }
  if (expectedRevision && actualRevision && expectedRevision !== actualRevision) {
    mismatch.expectedRevision = expectedRevision;
    mismatch.actualRevision = actualRevision;
  }

  return Object.keys(mismatch).length ? mismatch : null;
}

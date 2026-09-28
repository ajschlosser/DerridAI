/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "./http";
import { execute } from "./graphql/client";
import { SimilarValidatedClaimsDocument } from "./graphql/generated";

export type ClaimValidationStatus = "unvalidated" | "validated" | "rejected" | "unresolved";

export interface GeneratedClaimRecord {
  claim_id: string;
  claim_text: string;
  validation_status: ClaimValidationStatus;
  validated_by?: string | null;
  validated_at?: string | null;
}

export interface SimilarValidatedClaim {
  claim_id: string;
  claim_text: string;
  similarity: number;
  validated_by?: string | null;
  validated_at?: string | null;
  advisory: true;
  support: Array<{
    record_id: string;
    record_revision?: number | null;
    relation?: string | null;
    semantic?: Record<string, { value: unknown; authority?: string }>;
  }>;
}

export const claimsApi = {
  get: (claimId: string) =>
    apiRequest<{ claim: GeneratedClaimRecord }>(
      `/api/derridai/claims/${encodeURIComponent(claimId)}`,
    ),
  setValidation: (
    claimId: string,
    status: ClaimValidationStatus,
    record?: Record<string, unknown> | null,
  ) =>
    apiRequest<{
      claim: GeneratedClaimRecord;
      projection: { status: "indexed" | "removed" | "failed"; error: string };
    }>(`/api/derridai/claims/${encodeURIComponent(claimId)}/validation`, {
      method: "POST",
      // Only the record the auditor is looking at is sent, and only so its checked
      // attribution can be snapshotted next to the validated claim.
      body: JSON.stringify({ status, record: record ?? undefined }),
    }),
  // Read through the GraphQL façade (GET /api/derridai/claims/{id}/similar remains for compatibility).
  similar: async (claimId: string, limit = 5): Promise<{ items: SimilarValidatedClaim[] }> => {
    const { generated_claim } = await execute(SimilarValidatedClaimsDocument, {
      claim_id: claimId,
      limit,
    });
    return {
      items: generated_claim.similar_validated_claims.map((item) => ({
        ...item,
        advisory: true,
        support: item.support.map((support) => ({
          ...support,
          semantic: support.semantic as Record<string, { value: unknown; authority?: string }>,
        })),
      })),
    };
  },
};

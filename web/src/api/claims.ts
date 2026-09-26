/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "./http";

export type ClaimValidationStatus = "unvalidated" | "validated" | "rejected" | "unresolved";

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
  setValidation: (
    claimId: string,
    status: ClaimValidationStatus,
    record?: Record<string, unknown> | null,
  ) =>
    apiRequest<{
      claim: { claim_id: string; validation_status: ClaimValidationStatus };
      projection: { status: "indexed" | "removed" | "failed"; error: string };
    }>(`/api/derridai/claims/${encodeURIComponent(claimId)}/validation`, {
      method: "POST",
      // Only the record the auditor is looking at is sent, and only so its checked
      // attribution can be snapshotted next to the validated claim.
      body: JSON.stringify({ status, record: record ?? undefined }),
    }),
  similar: (claimId: string, limit = 5) =>
    apiRequest<{ items: SimilarValidatedClaim[] }>(
      `/api/derridai/claims/${encodeURIComponent(claimId)}/similar?limit=${limit}`,
    ),
};

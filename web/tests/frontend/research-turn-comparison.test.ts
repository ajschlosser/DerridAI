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
import { describe, expect, it } from "vitest";
import {
  claimStatusCounts,
  compareTurnEvidence,
} from "../../src/features/research/researchTurnComparison";
import type { ResearchResult } from "../../src/types/research";

const ev = (id: string, revision?: number, marker = "E1") => ({
  evidence_id: marker,
  inline_citation: `(${id})`,
  collection: "c",
  record: { record_id: id, ...(revision === undefined ? {} : { record_revision: revision }) },
});

describe("compareTurnEvidence", () => {
  it("aligns by Record, keeps each side's EvidenceRef, and flags revision differences", () => {
    const left = {
      evidence: [ev("r1", 1, "E1"), ev("r2", 1, "E2"), { evidence_id: "E3" }],
    } as ResearchResult;
    const right = { evidence: [ev("r1", 1, "E2"), ev("r2", 2, "E1"), ev("r3")] } as ResearchResult;
    const rows = compareTurnEvidence(left, right);
    const byId = Object.fromEntries(
      rows.filter((row) => row.recordId).map((row) => [row.recordId, row]),
    );
    expect(byId.r1.left?.evidence_id).toBe("E1");
    expect(byId.r1.right?.evidence_id).toBe("E2");
    expect(byId.r1.revisionDiffers).toBe(false);
    expect(byId.r2.revisionDiffers).toBe(true);
    expect(byId.r3.left).toBeNull();
    // Evidence without a Record ID is never matched to anything.
    expect(rows.filter((row) => !row.recordId)).toHaveLength(1);
  });
  it("counts claim validation as recorded", () => {
    const result = {
      claim_provenance: {
        claims: [
          { claim_id: "a", claim_text: "", validation_status: "validated" },
          { claim_id: "b", claim_text: "" },
          { claim_id: "c", claim_text: "", validation_status: "rejected" },
        ],
        support_bindings: [],
      },
    } as ResearchResult;
    expect(claimStatusCounts(result)).toEqual({ validated: 1, unvalidated: 1, rejected: 1 });
    expect(claimStatusCounts(null)).toEqual({});
  });
});

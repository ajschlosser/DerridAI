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
import { ref } from "vue";
import type { CorpusBuild, CorpusRecord } from "../../src/api/pdfCorpus";
import type { ReviewQueue } from "../../src/types/corpus";
import { recordIssueKinds, recordState } from "../../src/domain/corpusReview";
import { useCorpusBuildLifecycle } from "../../src/composables/useCorpusBuildLifecycle";

const record = (overrides: Partial<CorpusRecord> = {}): CorpusRecord => ({
  record_id: "r1",
  text: "Source passage",
  text_length: 14,
  source_block_ids: ["b1"],
  source_spans: [],
  ...overrides,
});
const build = (overrides: Partial<CorpusBuild> = {}): CorpusBuild => ({
  build_id: "build",
  asset_id: "asset",
  source_filename: "source.pdf",
  source_sha256: "sha",
  status: "awaiting_review",
  stage: "review",
  progress: 0.9,
  created_at: "",
  record_count: 3,
  accepted_count: 0,
  needs_review_count: 1,
  profile_id: "derrida-scholarly-v12",
  ...overrides,
});

describe("record review domain", () => {
  it("uses explicit server issues over stale local reasons", () => {
    expect(
      recordIssueKinds(
        record({ review_issue_codes: [], needs_review: true, review_reason: "boundary" }),
      ),
    ).toEqual([]);
    expect(
      recordIssueKinds(record({ review_issue_codes: ["source", "metadata", "future-code"] })),
    ).toEqual(["source", "metadata"]);
  });
  it("keeps authoritative review state ahead of legacy flags", () => {
    expect(recordState(record({ review_state: "metadata", accepted: true }))).toBe("metadata");
    expect(recordState(record({ accepted: true }))).toBe("accepted");
    expect(
      recordState(record({ needs_review: true, review_reason: "Split boundary requires review" })),
    ).toBe("topology");
  });
});

describe("corpus lifecycle composable", () => {
  it("unlocks only text after the current preparation's validated topology milestone", () => {
    const current = ref<CorpusBuild | null>(
      build({
        status: "running",
        stage: "constructing_records",
        text_review_available_at: "2026-10-03T00:00:00Z",
        topology_validation: { valid: true },
      }),
    );
    const view = useCorpusBuildLifecycle(current, ref(3), ref<ReviewQueue>("all"), ref(false));
    expect(view.textReviewLocked.value).toBe(false);
    expect(view.reviewLocked.value).toBe(true);
    expect(view.structuralReviewLocked.value).toBe(true);
    current.value!.stage = "document_intelligence";
    expect(view.textReviewLocked.value).toBe(false);
    current.value!.stage = "segmenting";
    expect(view.textReviewLocked.value).toBe(true);
    current.value!.stage = "constructing_records";
    current.value!.topology_validation = { valid: false };
    expect(view.textReviewLocked.value).toBe(true);
    current.value!.topology_validation = { valid: true };
    current.value!.text_review_available_at = null;
    expect(view.textReviewLocked.value).toBe(true);
  });
  it("reacts to the build/review/finish cycle without treating enrichment as structural review", () => {
    const current = ref<CorpusBuild | null>(null),
      total = ref(0),
      queue = ref<ReviewQueue>("all"),
      requested = ref(false);
    const view = useCorpusBuildLifecycle(current, total, queue, requested);
    expect(view.showBuildConfiguration.value).toBe(true);
    current.value = build({ status: "running", stage: "segmenting" });
    expect(view.reviewLocked.value).toBe(true);
    current.value.stage = "enriching";
    expect(view.reviewLocked.value).toBe(false);
    expect(view.structuralReviewLocked.value).toBe(false);
    current.value.stage = "metadata_enrichment_rerun";
    expect(view.reviewLocked.value).toBe(false);
    expect(view.structuralReviewLocked.value).toBe(false);
    current.value.stage = "finalizing_review";
    expect(view.reviewLocked.value).toBe(false);
    expect(view.structuralReviewLocked.value).toBe(false);
    for (const stage of ["preparing", "constructing_topology", "document_intelligence"]) {
      current.value.stage = stage;
      expect(view.reviewLocked.value).toBe(true);
      expect(view.structuralReviewLocked.value).toBe(true);
    }
    current.value = build({ accepted_count: 2, rejected_count: 1 });
    expect(view.finishPhase.value).toBe(true);
    expect(view.showReviewWorkspace.value).toBe(false);
    // A Finish blocker that opens the "all" queue must still leave the Finish screen.
    requested.value = true;
    expect(view.showReviewWorkspace.value).toBe(true);
    requested.value = false;
    queue.value = "rejected";
    expect(view.showReviewWorkspace.value).toBe(true);
  });
  it("honors manifest review, resume eligibility, and authoritative queue counts", () => {
    const current = ref<CorpusBuild | null>(build({ status: "awaiting_manifest_review" }));
    const view = useCorpusBuildLifecycle(current, ref(3), ref<ReviewQueue>("all"), ref(false));
    expect(view.hasRecordTopology.value).toBe(false);
    current.value = build({
      status: "interrupted",
      resumable: true,
      review_queue_counts: { pending: 1, ready: 0, issues: 1 },
    });
    expect(view.canResume.value).toBe(true);
    expect(view.pendingCount.value).toBe(1);
    expect(view.readyCount.value).toBe(0);
    current.value.status = "running";
    expect(view.canResume.value).toBe(false);
  });
});

describe("operational record keys", () => {
  it("never surface as scholarly metadata to review", async () => {
    const { reviewableMetadataFieldNames } = await import(
      "../../src/features/corpus-builder/domain/recordMetadata"
    );
    const record = {
      record_id: "r1",
      boundary_evidence: { after_block_id: "b1" },
      lineage: { operation: "split" },
      nlp_candidates: { status: "ok" },
      text_review_source: "human_split",
      field_assertions: {
        x: [{ assertion_id: "a", field_name: "boundary_evidence" }],
        y: [{ assertion_id: "b", field_name: "speaker" }],
      },
    };
    const names = reviewableMetadataFieldNames(record as never, null);
    expect(names).not.toContain("boundary_evidence");
    expect(names).not.toContain("lineage");
    expect(names).not.toContain("nlp_candidates");
    expect(names).toContain("speaker");
  });
});

describe("memory pre-fill bookkeeping", () => {
  it("does not treat memory hints as metadata fields", async () => {
    const { isOperationalKey } = await import(
      "../../src/features/corpus-builder/domain/recordMetadata"
    );
    expect(isOperationalKey("memory_hints")).toBe(true);
    expect(isOperationalKey("memory_prefill")).toBe(true);
    expect(isOperationalKey("speaker")).toBe(false);
  });
});

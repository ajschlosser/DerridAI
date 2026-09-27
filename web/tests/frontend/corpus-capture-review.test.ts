// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import type { CaptureCandidate } from "../../src/api/corpus";
import {
  acquirableCount,
  acquisitionOutcome,
  groupCandidates,
  optionsFromIncludes,
  stepForCapture,
} from "../../src/domain/captureReview";

function candidate(
  id: string,
  overrides: Partial<CaptureCandidate> = {},
): CaptureCandidate {
  return {
    candidate_id: id,
    provider: "wikisource",
    provider_item_id: id,
    title: "De la grammatologie",
    document_author: "Jacques Derrida",
    contribution_role: "author",
    document_languages: ["fr"],
    original_language: "fr",
    source_project_language: "fr",
    translators: [],
    editors: [],
    publication_year: 1967,
    edition: null,
    source_uri: `https://fr.wikisource.org/wiki/${id}`,
    catalog_uri: null,
    wikidata_work_id: "Q-work",
    wikidata_edition_id: null,
    canonical_work_id: "work-1",
    relationship_to_work: "original_language_edition",
    reconciliation_status: "exact_identity",
    possible_duplicates: null,
    identity_confidence: "exact",
    selection_status: "selected",
    selection_reason: "default",
    acquisition_status: "pending",
    source_document_id: null,
    digital_duplicate_of: null,
    error: null,
    upstream_status: "present",
    metadata_changed_fields: null,
    discovery_method: "wikidata_sitelink",
    discovery_evidence: {},
    discovered_at: "2026-09-27T00:00:00Z",
    acquired_at: null,
    rights_status: null,
    rights_source: null,
    ...overrides,
  };
}

describe("Corpus Capture review domain", () => {
  it("resumes durable captures at the step implied by their status and active job", () => {
    expect(
      stepForCapture({
        status: "interrupted",
        discovery_completed_at: "2026-09-27T00:00:00Z",
        active_job: null,
      }),
    ).toBe("review");
    expect(
      stepForCapture({
        status: "complete",
        discovery_completed_at: "2026-09-27T00:00:00Z",
        active_job: null,
      }),
    ).toBe("done");
    expect(
      stepForCapture({
        status: "acquiring",
        discovery_completed_at: "2026-09-27T00:00:00Z",
        active_job: {
          id: "capture-job",
          type: "corpus_capture",
          mode: "acquire",
          status: "running",
          stage: "acquiring",
          stage_detail: "",
          completed: 1,
          total: 2,
        },
      }),
    ).toBe("acquiring");
  });

  it("maps reviewer include choices to the persisted capture contract", () => {
    expect(
      optionsFromIncludes(
        ["gutenberg", "wikisource"],
        {
          authored: true,
          translations: true,
          translator: true,
          editor: false,
          other: false,
        },
        ["fr"],
      ),
    ).toEqual({
      providers: ["gutenberg", "wikisource"],
      roles: ["author", "coauthor", "translator"],
      include_translations: true,
      languages: ["fr"],
    });
  });

  it("groups editions by canonical work without merging candidates and puts originals first", () => {
    const translation = candidate("translation", {
      title: "Of Grammatology",
      document_languages: ["en"],
      relationship_to_work: "translation",
      translators: ["Gayatri Chakravorty Spivak"],
    });
    const original = candidate("original");
    const groups = groupCandidates([translation, original], "en");

    expect(groups).toHaveLength(1);
    expect(groups[0].items.map((item) => item.candidate_id)).toEqual(["translation", "original"]);
    expect(groups[0].languages).toHaveLength(2);
    expect(groups[0].languages[0].codes).toEqual(["fr"]);
    expect(groups[0].languages[0].items[0].candidate_id).toBe("original");
    expect(groups[0].languages[1].codes).toEqual(["en"]);
  });

  it("summarizes acquisition outcomes and retries only selected unfinished candidates", () => {
    const rows = [
      candidate("registered-a", {
        acquisition_status: "registered",
        source_document_id: "source-1",
      }),
      candidate("registered-b", {
        acquisition_status: "registered",
        source_document_id: "source-1",
      }),
      candidate("failed", {
        acquisition_status: "failed",
        error: { code: "network_timeout", message: "Timed out" },
      }),
      candidate("cancelled", { acquisition_status: "cancelled" }),
      candidate("pending", { acquisition_status: "pending" }),
      candidate("excluded", {
        selection_status: "excluded",
        acquisition_status: "pending",
      }),
    ];

    expect(acquisitionOutcome(rows)).toMatchObject({
      registered: 2,
      failed: 1,
      cancelled: 1,
      pending: 1,
      selected: 5,
      registeredSourceIds: ["source-1"],
    });
    expect(acquirableCount(rows)).toBe(3);
  });
});

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

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CaptureCandidate, CorpusCapture } from "../../api/corpus";
import CaptureCompletion from "./CaptureCompletion.vue";

const capture: CorpusCapture = {
  capture_id: "capture-derrida",
  author: {
    canonical_name: "Jacques Derrida",
    wikidata_qid: "Q130631",
    birth_year: 1930,
    death_year: 2004,
  },
  options: {
    providers: ["gutenberg", "wikisource"],
    roles: ["author", "coauthor"],
    include_translations: true,
    languages: null,
  },
  status: "partial",
  phase: "acquiring",
  created_at: "2026-09-27T00:00:00Z",
  discovery_completed_at: "2026-09-27T00:05:00Z",
  last_refreshed_at: null,
  provider_snapshots: [],
  summary: {
    candidates: 2,
    work_groups: 2,
    languages: { fr: 2 },
    providers: { wikisource: 2 },
    projects: { fr: 2 },
    roles: { author: 2 },
    translations: 0,
    possible_duplicates: 0,
    needs_review: 0,
    selected: 2,
    acquisition: { registered: 1, failed: 1 },
  },
  progress: { done: 2, total: 2 },
  warnings: [],
  errors: [],
  last_refresh_diff: null,
  discovery_contract_version: "1",
  active_job: null,
};

function candidate(
  id: string,
  title: string,
  overrides: Partial<CaptureCandidate> = {},
): CaptureCandidate {
  return {
    candidate_id: id,
    provider: "wikisource",
    provider_item_id: id,
    title,
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
    wikidata_work_id: null,
    wikidata_edition_id: null,
    canonical_work_id: id,
    relationship_to_work: "original_language_edition",
    reconciliation_status: "separate",
    possible_duplicates: null,
    identity_confidence: "probable",
    selection_status: "selected",
    selection_reason: "user",
    acquisition_status: "registered",
    source_document_id: `source-${id}`,
    digital_duplicate_of: null,
    error: null,
    upstream_status: "present",
    metadata_changed_fields: null,
    discovery_method: "wikisource_author",
    discovery_evidence: {},
    discovered_at: "2026-09-27T00:02:00Z",
    acquired_at: "2026-09-27T00:06:00Z",
    rights_status: null,
    rights_source: null,
    ...overrides,
  };
}

const candidates = [
  candidate("grammatology", "De la grammatologie"),
  candidate("voice", "La voix et le phénomène", {
    acquisition_status: "failed",
    source_document_id: null,
    acquired_at: null,
    error: { code: "network_timeout", message: "The source provider timed out." },
  }),
];

const meta = {
  title: "Corpus Builder/Capture/Completion",
  component: CaptureCompletion,
  args: { capture, candidates, busy: false },
  parameters: { layout: "padded" },
} satisfies Meta<typeof CaptureCompletion>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PartialWithRetry: Story = {};

export const Complete: Story = {
  args: {
    capture: {
      ...capture,
      status: "complete",
      summary: {
        ...capture.summary,
        acquisition: { registered: 2, failed: 0 },
      },
    },
    candidates: candidates.map((item, index) => ({
      ...item,
      acquisition_status: "registered" as const,
      source_document_id: `source-${index + 1}`,
      error: null,
    })),
  },
};

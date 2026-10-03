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
import CorpusMetadataIssues from "./CorpusMetadataIssues.vue";
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const build: any = {
  build_id: "build-aardvark",
  asset_id: "asset",
  source_filename: "book.pdf",
  source_sha256: "sha",
  status: "awaiting_metadata",
  stage: "metadata_review",
  progress: 0.96,
  created_at: "",
  record_count: 63,
  needs_review_count: 0,
  accepted_count: 63,
  rejected_count: 0,
  profile_id: "derrida-scholarly-v9",
  provider: "ollama",
  model: "Qwen3.8-27B",
  metadata_completed: 58,
  metadata_total: 63,
  request: { provider_profile_id: "primary" },
  metadata_issue_summary: {
    records_incomplete: 5,
    fields_unresolved: 7,
    auto_retry_fields: 5,
    human_review_fields: 2,
    by_field: { discourse_role: 3, region_type: 2, primary_text: 2 },
    by_reason: { llm_failed: 3, ambiguous: 2, evidence_failed: 2 },
    invalid_by_field: {},
    issues: [
      {
        record_id: "record-00012",
        field: "discourse_role",
        issue_type: "llm_failed",
        retryable: true,
        page_start: 18,
        page_end: 19,
      },
      {
        record_id: "record-00031",
        field: "region_type",
        issue_type: "ambiguous",
        retryable: false,
        page_start: 47,
        page_end: 48,
      },
    ],
  },
};
const meta = {
  title: "Corpus Builder/Review/Metadata Issues",
  component: CorpusMetadataIssues,
  args: { build },
} satisfies Meta<typeof CorpusMetadataIssues>;
export default meta;
type Story = StoryObj<typeof meta>;
export const NeedsAttention: Story = {};
export const RetryRunning: Story = {
  args: {
    build: {
      ...build,
      metadata_operation: {
        operation_id: "op-1",
        state: "running",
        records_total: 5,
        records_processed: 3,
        fields_total: 7,
        fields_resolved: 4,
        provider: "ollama",
        model: "Qwen3.8-27B",
        target_fields: ["region_type", "primary_text", "discourse_role"],
      },
    },
  },
};

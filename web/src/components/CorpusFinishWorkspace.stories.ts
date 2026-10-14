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
import CorpusFinishWorkspace from "./CorpusFinishWorkspace.vue";
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const base: any = {
  build_id: "build-lizard",
  asset_id: "asset",
  source_filename: "book.pdf",
  source_sha256: "sha",
  status: "awaiting_review",
  stage: "review",
  progress: 0.96,
  created_at: "",
  record_count: 63,
  accepted_count: 63,
  rejected_count: 0,
  profile_id: "derrida-scholarly-v9",
  metadata_completed: 58,
  metadata_total: 63,
  validation: { valid: true, source_valid: true, metadata_valid: true, coverage: 1 },
  source_quality: { blocking_page_count: 0 },
  metadata_issue_summary: {
    records_incomplete: 5,
    fields_unresolved: 7,
    auto_retry_fields: 5,
    human_review_fields: 2,
  },
  publication_readiness: {
    can_publish: false,
    next_action: "resolve_metadata",
    records_total: 63,
    records_reviewed: 63,
    records_accepted: 63,
    records_rejected: 0,
    records_pending: 0,
    blockers: [{ code: "required_metadata", count: 7 }],
  },
};
const meta = {
  title: "Corpus Builder/Workflow/Finish Workspace",
  component: CorpusFinishWorkspace,
  args: { build: base },
} satisfies Meta<typeof CorpusFinishWorkspace>;
export default meta;
type Story = StoryObj<typeof meta>;
export const MetadataBlocked: Story = {};
export const DocumentMetadataBlocked: Story = {
  args: {
    build: {
      ...base,
      metadata_completed: 63,
      metadata_issue_summary: { records_incomplete: 0, fields_unresolved: 0 },
      publication_readiness: {
        ...base.publication_readiness,
        next_action: "resolve_document_metadata",
        missing_document_fields: ["title", "document_author"],
        blockers: [
          { code: "required_document_metadata", count: 2, fields: ["title", "document_author"] },
        ],
      },
    },
  },
};
export const ReadyToPublish: Story = {
  args: {
    build: {
      ...base,
      status: "ready",
      stage: "ready",
      metadata_completed: 63,
      metadata_issue_summary: {
        records_incomplete: 0,
        fields_unresolved: 0,
        auto_retry_fields: 0,
        human_review_fields: 0,
      },
      publication_readiness: {
        ...base.publication_readiness,
        can_publish: true,
        next_action: "publish",
        blockers: [],
      },
    },
  },
};
export const Published: Story = {
  args: {
    build: {
      ...base,
      status: "ready",
      stage: "ready",
      metadata_completed: 63,
      metadata_issue_summary: { records_incomplete: 0, fields_unresolved: 0 },
      publication_readiness: {
        ...base.publication_readiness,
        can_publish: true,
        next_action: "download_publication",
        blockers: [],
        published: true,
      },
      publication: {
        publication_id: "pub-1",
        filename: "book.jsonl",
        sha256: "abc",
        record_count: 63,
        created_at: "2026-09-17T20:00:00Z",
      },
    },
  },
};
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    build: {
      ...base,
      metadata_completed: 63,
      metadata_issue_summary: { records_incomplete: 0, fields_unresolved: 0 },
      publication_readiness: {
        ...base.publication_readiness,
        next_action: "resolve_document_metadata",
        missing_document_fields: ["title", "document_author"],
        blockers: [
          { code: "required_document_metadata", count: 2, fields: ["title", "document_author"] },
        ],
      },
    },
  },
};

export const MixedAcceptedAndRejected: Story = {
  args: {
    build: {
      ...base,
      accepted_count: 40,
      rejected_count: 23,
      metadata_completed: 63,
      metadata_issue_summary: { records_incomplete: 0, fields_unresolved: 0 },
      publication_readiness: {
        ...base.publication_readiness,
        records_accepted: 40,
        records_rejected: 23,
        records_pending: 0,
        can_publish: true,
        next_action: "publish",
        blockers: [],
      },
    },
  },
};
export const ValidationIssuesGrouped: Story = {
  args: {
    build: {
      ...base,
      metadata_completed: 63,
      metadata_issue_summary: { records_incomplete: 0, fields_unresolved: 0 },
      validation: {
        valid: false,
        source_valid: true,
        metadata_valid: false,
        coverage: 0.97,
        validation_issues: [
          {
            code: "metadata_evidence",
            record_id: "of-grammatology-00042",
            field: "speaker",
            reason: "no valid source block",
          },
          {
            code: "metadata_evidence",
            record_id: "of-grammatology-00042",
            field: "position_holder",
            reason: "confidence 0.41 below 0.60",
          },
          {
            code: "citation",
            record_id: "of-grammatology-00042",
            field: "",
            reason: "citation is missing or incomplete",
          },
          {
            code: "metadata_schema",
            record_id: "of-grammatology-00107",
            field: "stance",
            reason: "value is not a supported enum value",
          },
        ],
      },
      publication_readiness: {
        ...base.publication_readiness,
        can_publish: false,
        next_action: "resolve_validation",
        blockers: [{ code: "metadata_validation", count: 4 }],
      },
    },
  },
};
export const NoPublishableRecords: Story = {
  args: {
    build: {
      ...base,
      accepted_count: 0,
      rejected_count: 63,
      metadata_completed: 63,
      metadata_issue_summary: { records_incomplete: 0, fields_unresolved: 0 },
      publication_readiness: {
        ...base.publication_readiness,
        records_accepted: 0,
        records_rejected: 63,
        records_pending: 0,
        can_publish: false,
        no_publishable_records: true,
        next_action: "no_publishable_records",
        blockers: [{ code: "no_publishable_records", count: 63 }],
      },
    },
  },
};

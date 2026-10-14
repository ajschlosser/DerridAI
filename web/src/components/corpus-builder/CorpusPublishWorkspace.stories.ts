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
import CorpusPublishWorkspace from "./CorpusPublishWorkspace.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture supplies only the fields the workspace reads.
const build: any = {
  build_id: "build-42",
  source_filename: "Of Grammatology.pdf",
  status: "awaiting_review",
  stage: "review",
  record_count: 177,
  accepted_count: 142,
  rejected_count: 4,
  metadata_issue_summary: { fields_unresolved: 0 },
  validation: { valid: true, source_valid: true, metadata_valid: true },
  publication_readiness: {
    can_publish: false,
    next_action: "review_records",
    blockers: [{ code: "record_review", count: 31 }],
    records_total: 177,
    records_reviewed: 146,
    records_accepted: 142,
    records_rejected: 4,
    records_pending: 31,
  },
};

const meta = {
  title: "Corpus Builder/Publish/Workspace",
  component: CorpusPublishWorkspace,
  args: { build, canPublishUnreviewed: true },
} satisfies Meta<typeof CorpusPublishWorkspace>;
export default meta;
type Story = StoryObj<typeof meta>;

export const UnreviewedRecords: Story = {};
export const Ready: Story = {
  args: {
    canPublishUnreviewed: false,
    build: {
      ...build,
      status: "ready",
      publication_readiness: {
        ...build.publication_readiness,
        can_publish: true,
        next_action: "publish",
        blockers: [],
        records_pending: 0,
        records_reviewed: 177,
      },
    },
  },
};
export const Published: Story = {
  args: {
    canPublishUnreviewed: false,
    build: {
      ...build,
      status: "published",
      stage: "published",
      publication: {
        publication_id: "publication-2026-09-25-001",
        record_count: 173,
        sha256: "abc123",
      },
    },
  },
};

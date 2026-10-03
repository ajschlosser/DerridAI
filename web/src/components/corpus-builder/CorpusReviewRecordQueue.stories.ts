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
import type { CorpusRecord } from "../../api/corpus";
import { queueRowFromRecord } from "../../features/corpus-builder/domain/queueRows";
import CorpusReviewRecordQueue from "./CorpusReviewRecordQueue.vue";

function record(
  recordId: string,
  reviewState: string,
  overrides: Partial<CorpusRecord> = {},
): CorpusRecord {
  return {
    record_id: recordId,
    text: "A representative record for queue presentation.",
    text_length: 47,
    inline_citation: "Derrida, p. 12",
    source_block_ids: ["block-1"],
    source_spans: [],
    review_state: reviewState,
    ...overrides,
  };
}

const rows = [
  record("record-enriching", "preparing"),
  record("record-enriching-2", "preparing"),
  record("record-preparing", "preparing"),
  record("record-ready", "ready", { metadata_enrichment_finished: true }),
  record("record-metadata", "metadata", {
    review_issue_codes: ["metadata", "source"],
  }),
  record("record-accepted", "accepted", { accepted: true }),
  record("record-rejected", "rejected", { rejected: true }),
].map(queueRowFromRecord);

const meta = {
  title: "Corpus Builder/Review/Record Queue",
  component: CorpusReviewRecordQueue,
  args: {
    rows,
    recordTotal: rows.length,
    selectedRecordId: "record-metadata",
    selectedReviewIds: new Set(["record-metadata"]),
    allVisibleSelected: false,
    loading: false,
    hydrated: true,
    disabled: false,
    activeProcessingRecordIds: new Set(["record-enriching", "record-enriching-2"]),
  },
} satisfies Meta<typeof CorpusReviewRecordQueue>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MixedStates: Story = {};

export const SourceWarning: Story = {
  args: {
    rows: [
      queueRowFromRecord(
        record("record-source", "source", {
          source_quality_issues: [{ code: "ocr_noise", severity: "warning" }],
        }),
      ),
    ],
    recordTotal: 1,
    selectedRecordId: "record-source",
  },
};

export const Empty: Story = {
  args: {
    rows: [],
    recordTotal: 0,
    selectedRecordId: "",
    selectedReviewIds: new Set(),
  },
};

export const Loading: Story = {
  args: {
    rows: [],
    recordTotal: 0,
    selectedRecordId: "",
    selectedReviewIds: new Set(),
    loading: true,
    hydrated: false,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};

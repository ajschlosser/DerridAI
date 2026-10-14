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
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import CorpusReviewEvidencePanel from "./CorpusReviewEvidencePanel.vue";

const record: CorpusRecord = {
  record_id: "record-1",
  text: "A representative record with reviewed evidence.",
  text_length: 46,
  source_block_ids: ["block-1", "block-2"],
  source_spans: [],
  metadata_evidence: {
    speaker: {
      block_ids: ["block-1"],
      confidence: 0.92,
      reason: "The speaker is explicit in the source.",
    },
    position_holder: {
      block_ids: [],
      confidence: 0.58,
      reason: "Requires review.",
    },
  },
};

const blocks: SourceBlock[] = [
  {
    block_id: "block-1",
    page: 12,
    bbox: [],
    type: "paragraph",
    text: "Derrida writes that the position must be distinguished from the position he attributes.",
    extraction_method: "pdf_text",
    confidence: 0.99,
  },
  {
    block_id: "block-2",
    page: 13,
    bbox: [],
    type: "paragraph",
    text: "The following paragraph continues the same argumentative movement.",
    extraction_method: "pdf_text",
    confidence: 0.98,
  },
];

const meta = {
  title: "Corpus Builder/Review/Evidence Panel",
  component: CorpusReviewEvidencePanel,
  args: {
    record,
    fields: ["speaker", "position_holder", "target", "stance"],
    selectedField: "speaker",
    blocks,
    evidenceBlockIds: new Set(["block-1"]),
    paginatedSource: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusReviewEvidencePanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SelectedEvidence: Story = {};

export const UnboundField: Story = {
  args: {
    selectedField: "position_holder",
    evidenceBlockIds: new Set(),
  },
};

export const Busy: Story = {
  args: {
    disabled: true,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};

export const WithSuggestions: Story = {
  args: { buildId: "build-1", llmRequest: { provider_profile_id: "local" } },
};

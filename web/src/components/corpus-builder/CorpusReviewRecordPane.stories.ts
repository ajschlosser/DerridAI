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
import CorpusReviewRecordPane from "./CorpusReviewRecordPane.vue";

const record = {
  record_id: "rec_0184",
  inline_citation: "(Derrida 1967, p. 12)",
  text: "Il n’y a pas de hors-texte.",
  text_length: 27,
  text_review_status: "unreviewed",
  review_reason: "Quotation attribution needs review.",
  source_block_ids: [],
  source_spans: [],
};

const meta = {
  title: "Corpus Builder/Review/Record Pane",
  component: CorpusReviewRecordPane,
  args: {
    record: record as never,
    buildId: "build-1",
    visible: true,
    queueCollapsed: false,
    editing: false,
    busy: false,
    locked: false,
    activitySummary: "",
    popout: null,
    textDraft: "",
    showContext: false,
    resolveSource: false,
  },
} satisfies Meta<typeof CorpusReviewRecordPane>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Reading: Story = {};
export const Editing: Story = { args: { editing: true, textDraft: "Il n’y a pas de hors-texte." } };
export const NothingSelected: Story = { args: { record: null } };
export const Loading: Story = { args: { record: null, loading: true } };
export const Failed: Story = { args: { record: null, loadError: "Network unavailable" } };
export const Missing: Story = { args: { record: null, loadError: "not_found" } };
export const Preparing: Story = { args: { locked: true } };

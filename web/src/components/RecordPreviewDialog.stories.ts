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
import RecordPreviewDialog from "./RecordPreviewDialog.vue";
import { openRecordPreviewDialog } from "../composables/recordPreviewDialog";

const meta = {
  title: "Jobs/Record Preview Dialog",
  component: RecordPreviewDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { RecordPreviewDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><RecordPreviewDialog /></div>`,
    methods: {
      open() {
        openRecordPreviewDialog({
          recordId: "rec-0001",
          subtitle: "Of Grammatology · grammatology.jsonl",
          stale: true,
          summary: {
            work: "Of Grammatology",
            pages: "158",
            citation: "Derrida, Of Grammatology, p. 158",
            proposalCount: 1,
            needsReview: true,
          },
          fields: [
            { key: "speaker", label: "Speaker", value: '"Derrida"', proposed: true },
            { key: "year", label: "Year", value: "1967", proposed: false },
          ],
          text: "There is nothing outside the text.",
          proposals: [
            {
              label: "Speaker",
              current: '"Derrida"',
              proposed: '"Rousseau"',
              rationale: "The passage paraphrases Rousseau.",
            },
          ],
          history: [{ when: "2026-10-02 14:00", field: "Year", source: "manual" }],
          copyKey: "f1::0",
          openFull: () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof RecordPreviewDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const StaleWithProposal: Story = {};

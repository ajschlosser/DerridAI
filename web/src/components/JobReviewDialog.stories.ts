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
import JobReviewDialog from "./JobReviewDialog.vue";
import { openJobReviewDialog, type JobReviewView } from "../composables/jobReviewDialog";

function story(view: JobReviewView) {
  return {
    render: () => ({
      components: { JobReviewDialog },
      template: `<div><button class="btn" type="button" @click="open">Open</button><JobReviewDialog /></div>`,
      methods: {
        open() {
          openJobReviewDialog(view, {
            apply: async () => true,
            rejectSelected: async () => true,
            discard: () => undefined,
            refresh: () => undefined,
            previewRow: () => undefined,
            previewUnchanged: () => undefined,
            onClose: () => undefined,
          });
        },
      },
    }),
  };
}

const base: JobReviewView = {
  title: "LLM review changes",
  subtitle: "3/10 · 2 pending",
  active: true,
  completed: 3,
  remaining: 7,
  noChangeCount: 1,
  resolution: {
    acceptedResults: 0,
    acceptedFields: 0,
    rejectedResults: 0,
    rejectedFields: 0,
    state: "pending",
  },
  failures: ["r-9: provider timeout"],
  rows: [
    {
      recordId: "r-1",
      copyKey: "file:1",
      stale: false,
      isText: false,
      field: "Work",
      currentHtml: "<del>Of Grammatology</del>",
      proposedHtml: "<ins>De la grammatologie</ins>",
      rationale: "Matches the title page.",
    },
    {
      recordId: "r-2",
      copyKey: "file:2",
      stale: true,
      isText: true,
      field: "Text",
      currentHtml: "old",
      proposedHtml: "new",
      rationale: "",
    },
  ],
  unchanged: [{ recordId: "r-3", work: "Of Grammatology", stale: false }],
  discard: "stop",
  hasSuccessful: true,
};

const meta = {
  title: "Jobs/Job Review Dialog",
  component: JobReviewDialog,
  parameters: { layout: "centered" },
} satisfies Meta<typeof JobReviewDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = story(base);
export const NothingProposed: Story = story({
  ...base,
  active: false,
  rows: [],
  failures: [],
  discard: "none",
});

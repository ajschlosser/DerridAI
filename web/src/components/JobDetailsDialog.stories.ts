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
import JobDetailsDialog from "./JobDetailsDialog.vue";
import { openJobDetailsDialog, type JobDetailsRequest } from "../composables/jobDetailsDialog";

function story(request: JobDetailsRequest) {
  return {
    render: () => ({
      components: { JobDetailsDialog },
      template: `<div><button class="btn" type="button" @click="open">Open</button><JobDetailsDialog /></div>`,
      methods: {
        open() {
          openJobDetailsDialog(request);
        },
      },
    }),
  };
}

const base: JobDetailsRequest = {
  title: "Metadata proposals details",
  subtitle: "job-1 · Running · Created 10:02",
  facts: [
    { name: "Operation", value: "llm" },
    { name: "Progress", value: "3/10" },
  ],
  fatalError: "",
  requestJson: '{\n  "mode": "metadata"\n}',
  events: [
    { when: "10:02", stage: "Queued", detail: "", latest: false },
    { when: "10:03", stage: "Running", detail: "3/10 · record r-3", latest: true },
  ],
  resultJson: '{\n  "pending_result_count": 3\n}',
  cancel: "cancel",
  onCancel: () => undefined,
  openResult: { label: "Review partial results", run: () => undefined },
};

const meta = {
  title: "Jobs/Job Details Dialog",
  component: JobDetailsDialog,
  parameters: { layout: "centered" },
} satisfies Meta<typeof JobDetailsDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = story(base);
export const FailedWithoutEvents: Story = story({
  ...base,
  fatalError: "Provider unreachable",
  events: [],
  cancel: "none",
  openResult: null,
});

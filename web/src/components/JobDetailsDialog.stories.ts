// Copyright 2026 Aaron John Schlosser, PhD.
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

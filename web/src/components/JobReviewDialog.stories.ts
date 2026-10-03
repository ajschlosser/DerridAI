// Copyright 2026 Aaron John Schlosser, PhD.
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

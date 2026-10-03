// Copyright 2026 Aaron John Schlosser, PhD.
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

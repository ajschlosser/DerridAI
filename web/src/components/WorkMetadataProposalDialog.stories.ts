// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorkMetadataProposalDialog from "./WorkMetadataProposalDialog.vue";
import { openWorkMetadataProposalDialog } from "../composables/workMetadataProposalDialog";

const meta = {
  title: "Works/Work Metadata Proposal Dialog",
  component: WorkMetadataProposalDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { WorkMetadataProposalDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><WorkMetadataProposalDialog /></div>`,
    methods: {
      open() {
        openWorkMetadataProposalDialog({
          jobLabel: "Populate metadata · 3 works",
          entries: [
            {
              work: "Of Grammatology",
              recordCount: 128,
              fieldLabel: "Publisher",
              current: "—",
              proposed: "Johns Hopkins University Press",
              rationale: "Open Library edition match",
              confidence: 0.92,
            },
            {
              work: "Of Grammatology",
              recordCount: 128,
              fieldLabel: "Publication year",
              current: "1967",
              proposed: "1976",
              rationale: "",
              confidence: null,
            },
          ],
          unmatched: [{ work: "Untitled lecture", message: "No catalogue match" }],
          apply: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof WorkMetadataProposalDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithProposals: Story = {};

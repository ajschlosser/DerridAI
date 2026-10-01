/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusRecordResearchClaims from "./CorpusRecordResearchClaims.vue";

const meta: Meta<typeof CorpusRecordResearchClaims> = {
  title: "Corpus Builder/Review/Research Claims",
  component: CorpusRecordResearchClaims,
  args: {
    buildId: "build-1",
    recordId: "r-7",
    load: async () => ({
      items: [
        {
          claim_id: "c-1",
          claim_text: "Unconditional hospitality exceeds every law of hospitality.",
          relation: "supports",
          record_revision: 4,
          validated_by: "ann",
          citation: { inline: "(Author, Of Hospitality, 25)" },
          binding_status: "current",
        },
        {
          claim_id: "c-2",
          claim_text: "The host becomes hostage.",
          relation: "contextualizes",
          record_revision: 2,
          validated_by: "ann",
          citation: {},
          binding_status: "stale",
        },
      ],
    }),
  },
};
export default meta;
type Story = StoryObj<typeof CorpusRecordResearchClaims>;
export const Default: Story = {};
export const None: Story = { args: { load: async () => ({ items: [] }) } };

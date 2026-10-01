import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchClaimReviewPanel from "./ResearchClaimReviewPanel.vue";

const meta: Meta<typeof ResearchClaimReviewPanel> = {
  title: "Research/Claim Review Panel",
  component: ResearchClaimReviewPanel,
  parameters: { layout: "padded" },
  args: {
    refreshAuthoritative: false,
    evidence: [
      {
        evidence_id: "E1",
        inline_citation: "(Author, 25)",
        record: { record_id: "r1", record_revision: 2 },
      },
      {
        evidence_id: "E2",
        inline_citation: "(Author, 77)",
        record: { record_id: "r2", record_revision: 1 },
      },
    ],
    provenance: {
      claims: [
        {
          claim_id: "c1",
          claim_text: "Unconditional hospitality exceeds the conditions that regulate it.",
          validation_status: "unvalidated",
        },
        {
          claim_id: "c2",
          claim_text: "The conditional laws of hospitality remain necessary in political life.",
          validation_status: "validated",
          validated_by: "reviewer",
        },
      ],
      support_bindings: [
        {
          support_binding_id: "s1",
          claim_id: "c1",
          record_id: "r1",
          record_revision: 2,
          relation: "supports",
          validation_status: "unvalidated",
          citation: { inline: "(Author, 25)", evidence_marker: "E1" },
        },
        {
          support_binding_id: "s2",
          claim_id: "c2",
          record_id: "r2",
          record_revision: 1,
          relation: "supports",
          validation_status: "validated",
          citation: { inline: "(Author, 77)", evidence_marker: "E2" },
        },
      ],
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const MissingSupport: Story = {
  args: {
    provenance: {
      claims: [
        {
          claim_id: "c3",
          claim_text: "A generated claim whose evidence binding was not retained.",
          validation_status: "unvalidated",
        },
      ],
      support_bindings: [],
    },
  },
};

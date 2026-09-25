import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordWorkspaceHeader from "./RecordWorkspaceHeader.vue";
const meta = {
  title: "Record Workspace/Workspace Header",
  component: RecordWorkspaceHeader,
  args: {
    work: "Adieu to Emmanuel Levinas",
    author: "Jacques Derrida",
    year: 1999,
    pages: "pp. 20–21",
    recordId: "adieu-00042",
    position: "42 of 318",
    evidenceSelected: true,
    canEdit: true,
    canEvidence: true,
    canReview: true,
    canUpsert: true,
    canLlm: true,
    canHistory: true,
    canPdf: true,
    hasHistory: true,
    hasPrevious: true,
    hasNext: true,
  },
} satisfies Meta<typeof RecordWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const ReadOnlyResearcher: Story = {
  args: {
    canEdit: false,
    canReview: false,
    canUpsert: false,
    canLlm: false,
    canHistory: false,
    canPdf: false,
    evidenceSelected: false,
  },
};

export const LongWorkTitle: Story = {
  args: {
    work: "The Beast and the Sovereign, Volume II: Seminar of Jacques Derrida, 2002–2003 — Session on Robinson Crusoe, sovereignty, and the living",
    pages: "pp. 247–263",
  },
};

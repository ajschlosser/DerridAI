import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordReadingPane from "./RecordReadingPane.vue";
const text =
  "The relation to the other is not merely one relation among others. Responsibility is exposed in the face of the other, and this exposure interrupts the sovereignty of the same.";
const meta = {
  title: "Record Workspace/Reading Pane",
  component: RecordReadingPane,
  args: {
    text,
    findQuery: "other",
    wordCount: 30,
    characterCount: text.length,
    canAnnotate: true,
    annotations: [
      {
        id: "a1",
        field: "text",
        quote: "Responsibility is exposed in the face of the other",
        note: "Useful formulation of responsibility.",
        tags: ["ethics"],
        author: "researcher",
        created_at: "2026-09-14T12:00:00Z",
        removable: true,
      },
    ],
  },
} satisfies Meta<typeof RecordReadingPane>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const ResearcherSummary: Story = { args: { summaryMode: true, canAnnotate: false } };

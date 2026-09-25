import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordIndexTerms from "./RecordIndexTerms.vue";
const meta = {
  title: "Record Workspace/Index Terms",
  component: RecordIndexTerms,
  args: {
    title: "Concepts",
    field: "concepts",
    values: ["responsibility", "the Other", "death", "hospitality"],
    editable: true,
  },
} satisfies Meta<typeof RecordIndexTerms>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Editable: Story = {};
export const ReadOnly: Story = { args: { editable: false } };

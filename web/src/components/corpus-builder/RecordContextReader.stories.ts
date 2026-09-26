import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordContextReader from "./RecordContextReader.vue";

// Context is fetched from the API; without a backend the story shows the record alone.
const meta = {
  title: "Corpus Builder/Review/Record Context Reader",
  component: RecordContextReader,
  args: {
    buildId: "b1",
    recordId: "r3",
    text: "Hospitality is culture itself and not simply one ethic among others.",
    showContext: true,
  },
} satisfies Meta<typeof RecordContextReader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const ContextOff: Story = { args: { showContext: false } };

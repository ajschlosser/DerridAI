import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SearchSelectionBar from "./SearchSelectionBar.vue";
const meta: Meta<typeof SearchSelectionBar> = {
  title: "Search/Selection Bar",
  component: SearchSelectionBar,
  args: { count: 12, canReview: true, canBulkEdit: true },
};
export default meta;
type Story = StoryObj<typeof SearchSelectionBar>;
export const Default: Story = {};

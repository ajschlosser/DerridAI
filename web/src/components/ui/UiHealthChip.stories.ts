import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiHealthChip from "./UiHealthChip.vue";
const meta = {
  title: "Foundations/Feedback/Health Chip",
  component: UiHealthChip,
  args: { available: true, label: "Local Chroma · ./data/chroma", detail: "Heartbeat ok" },
} satisfies Meta<typeof UiHealthChip>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ready: Story = {};
export const Unavailable: Story = {
  args: { available: false, label: "Chroma unavailable", detail: "connection refused" },
};

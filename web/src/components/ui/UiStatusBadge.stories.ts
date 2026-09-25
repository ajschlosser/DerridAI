import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiStatusBadge from "./UiStatusBadge.vue";
const meta = {
  title: "Foundations/Feedback/Status Badge",
  component: UiStatusBadge,
  args: { label: "Needs review", tone: "warning", help: "A reviewer decision is required." },
} satisfies Meta<typeof UiStatusBadge>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Warning: Story = {};
export const Success: Story = { args: { label: "Confirmed", tone: "success" } };
export const Danger: Story = { args: { label: "Failed", tone: "danger" } };
export const Info: Story = { args: { label: "Processing", tone: "info" } };

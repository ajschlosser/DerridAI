import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiButton from "./UiButton.vue";
const meta = {
  title: "Foundations/Actions/Button",
  component: UiButton,
  args: { label: "Save changes", variant: "primary" },
} satisfies Meta<typeof UiButton>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Primary: Story = {};
export const Secondary: Story = { args: { variant: "default", label: "Cancel" } };
export const Danger: Story = { args: { variant: "danger", label: "Delete" } };
export const DisabledWithReason: Story = {
  args: {
    disabled: true,
    disabledReason: "Resolve the active operation first.",
    label: "Unavailable",
  },
};

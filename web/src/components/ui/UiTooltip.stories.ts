import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiTooltip from "./UiTooltip.vue";

const meta = {
  title: "UI/Tooltip",
  component: UiTooltip,
  args: {
    text: "Evidence must be bound to the current record source.",
    label: "About evidence requirements",
  },
} satisfies Meta<typeof UiTooltip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Below: Story = { args: { placement: "bottom" } };

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ActionButton from "./ActionButton.vue";

const meta = {
  title: "Components/ActionButton",
  component: ActionButton,
  args: {
    label: "Sync work",
    icon: "database",
    disabled: false,
    disabledReason: "",
  },
} satisfies Meta<typeof ActionButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Primary: Story = { args: { kind: "primary", label: "Run RAG", icon: "spark" } };
export const DisabledWithReason: Story = {
  args: {
    disabled: true,
    disabledReason: "Create a vector database before syncing this work.",
  },
};

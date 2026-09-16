import type { Meta, StoryObj } from "@storybook/vue3-vite";
import AppIcon from "./AppIcon.vue";

const meta = {
  title: "Components/AppIcon",
  component: AppIcon,
  args: { name: "database" },
} satisfies Meta<typeof AppIcon>;

export default meta;
type Story = StoryObj<typeof meta>;
export const Database: Story = {};
export const Research: Story = { args: { name: "spark" } };
export const Pdf: Story = { args: { name: "pdf" } };

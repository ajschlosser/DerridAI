/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ProviderSaveBar from "./ProviderSaveBar.vue";

const meta = {
  title: "Providers/Save bar",
  component: ProviderSaveBar,
  args: { saving: false, canSave: true },
} satisfies Meta<typeof ProviderSaveBar>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Unsaved: Story = {};
export const Saving: Story = { args: { saving: true } };

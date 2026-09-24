/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { createPinia, setActivePinia } from "pinia";
import MetadataSchemasView from "./MetadataSchemasView.vue";

const meta = {
  title: "System/Metadata Schemas",
  component: MetadataSchemasView,
} satisfies Meta<typeof MetadataSchemasView>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Page: Story = {
  render: () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    return {
      components: { MetadataSchemasView },
      template: "<MetadataSchemasView />",
    };
  },
};

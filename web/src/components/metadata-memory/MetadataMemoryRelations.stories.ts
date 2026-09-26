// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MetadataMemoryRelations from "./MetadataMemoryRelations.vue";

const meta = {
  title: "Metadata memory/Relations",
  component: MetadataMemoryRelations,
} satisfies Meta<typeof MetadataMemoryRelations>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Collapsed: Story = {};
export const Open: Story = {
  render: () => ({
    components: { MetadataMemoryRelations },
    template: "<MetadataMemoryRelations open />",
  }),
};

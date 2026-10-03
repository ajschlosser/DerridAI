/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VectorCollectionRail from "./VectorCollectionRail.vue";
const collections = [
  { name: "derrida-primary", count: 12840, retrieval_mode: "hybrid", status: "ready" },
  {
    name: "derrida_en",
    count: 6120,
    retrieval_mode: "semantic",
    status: "ready",
    collection_role: "language",
  },
];
const meta = {
  title: "Corpus Data/Collection Rail",
  component: VectorCollectionRail,
  args: { collections, activeName: "derrida-primary", filter: "" },
} satisfies Meta<typeof VectorCollectionRail>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Populated: Story = {};
export const FilteredEmpty: Story = { args: { collections: [], filter: "zzz" } };

export const ProvidersUnavailable: Story = {
  args: {
    canCreate: false,
    createDisabledReason: "Provider choices are unavailable. Retry before creating a collection.",
  },
};

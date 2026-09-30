/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SemanticGraphEntityIndex from "./SemanticGraphEntityIndex.vue";

const items = Array.from({ length: 8 }, (_, i) => ({
  id: `n${i}`,
  type: i % 2 ? "person" : "concept",
  label: `Entity ${i + 1}`,
  aliases: i % 3 ? [] : ["alias one", "alias two"],
  mention_count: 100 - i,
  record_count: 4,
  degree: 3,
}));

const meta = {
  title: "Corpus Builder/Review/Semantic Entity Index",
  component: SemanticGraphEntityIndex,
  args: {
    nodeTotal: 240,
    index: { total: 240, offset: 0, limit: 50, sort: "mentions" as const, items },
    loading: false,
    selectedNodeId: "n2",
    hueClass: (type: string) => (type === "person" ? "hue-2" : "hue-1"),
    sort: "mentions" as const,
    offset: 0,
  },
} satisfies Meta<typeof SemanticGraphEntityIndex>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FirstPage: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };

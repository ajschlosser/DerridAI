/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSemanticWorkspace from "./CorpusSemanticWorkspace.vue";

const meta = {
  title: "Corpus Builder/Review/Semantic workspace",
  component: CorpusSemanticWorkspace,
  args: { buildId: "build-story", summary: { nodes: 1240, edges: 3810 } as never },
} satisfies Meta<typeof CorpusSemanticWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The closed state: one slim trigger with the graph size, in place of two disclosures. */
export const Closed: Story = {};

export const NoGraphYet: Story = { args: { summary: null } };

export const Disabled: Story = { args: { disabled: true } };

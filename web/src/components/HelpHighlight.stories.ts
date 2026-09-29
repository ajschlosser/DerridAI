/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import HelpHighlight from "./HelpHighlight.vue";

const meta = {
  title: "Help/Search highlight",
  component: HelpHighlight,
  args: {
    text: "Reranking reorders retrieved passages with a cross-encoder before they reach the model.",
    query: "rerank cross-encoder",
  },
} satisfies Meta<typeof HelpHighlight>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Matching: Story = {};
export const NoQuery: Story = { args: { query: "" } };

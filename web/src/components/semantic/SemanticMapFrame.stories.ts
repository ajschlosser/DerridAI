/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SemanticMapFrame from "./SemanticMapFrame.vue";

const sources = [
  {
    id: "r1",
    work: "Of Grammatology",
    concepts: ["trace", "writing"],
    topics: ["presence"],
    persons: ["Rousseau"],
  },
  {
    id: "r2",
    work: "Writing and Difference",
    concepts: ["trace", "différance"],
    topics: ["presence"],
    persons: ["Levinas"],
  },
];

const meta = {
  title: "Corpus/Semantic map",
  component: SemanticMapFrame,
  args: { variant: "page", sources, focusId: "r1", showClose: false },
} satisfies Meta<typeof SemanticMapFrame>;
export default meta;
type Story = StoryObj<typeof meta>;

export const DedicatedView: Story = {};
export const AboveRecord: Story = { args: { variant: "record", showClose: true } };
export const Sidebar: Story = { args: { variant: "sidebar" } };
export const Dialog: Story = { args: { variant: "modal" } };
export const Empty: Story = { args: { sources: [], focusId: "" } };

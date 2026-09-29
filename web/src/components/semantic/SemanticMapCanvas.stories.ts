/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { buildSemanticMap } from "../../domain/semanticMap";
import SemanticMapCanvas from "./SemanticMapCanvas.vue";

const graph = buildSemanticMap(
  [
    {
      id: "r1",
      work: "Of Grammatology",
      concepts: ["trace", "writing"],
      topics: ["presence"],
      persons: ["Rousseau"],
    },
  ],
  "r1",
);

const meta = {
  title: "Corpus/Semantic map canvas",
  component: SemanticMapCanvas,
  args: { graph },
} satisfies Meta<typeof SemanticMapCanvas>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Draggable: Story = {};

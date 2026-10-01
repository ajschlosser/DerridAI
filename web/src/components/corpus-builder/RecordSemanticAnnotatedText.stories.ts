/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordSemanticAnnotatedText from "./RecordSemanticAnnotatedText.vue";

const text = "Heidegger questions the metaphysics of presence, and Author reads the trace.";
const at = (surface: string) => ({
  start: text.indexOf(surface),
  end: text.indexOf(surface) + surface.length,
  text: surface,
});

const meta = {
  title: "Corpus Builder/Review/Semantic Annotated Text",
  component: RecordSemanticAnnotatedText,
  args: {
    text,
    idPrefix: "story",
    mentions: [
      { ...at("Heidegger"), layer: "entity", tag: "PERSON", node_id: "person:heidegger" },
      { ...at("presence"), layer: "pos", tag: "NOUN" },
      { ...at("Author"), layer: "ner", tag: "PERSON", node_id: "person:author" },
    ],
  },
} satisfies Meta<typeof RecordSemanticAnnotatedText>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllLayers: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };

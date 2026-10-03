/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordSemanticAnnotatedText from "./RecordSemanticAnnotatedText.vue";

const text = "Heidegger questions the metaphysics of presence, and Derrida reads the trace.";
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
      { ...at("Derrida"), layer: "ner", tag: "PERSON", node_id: "person:derrida" },
    ],
  },
} satisfies Meta<typeof RecordSemanticAnnotatedText>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllLayers: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };

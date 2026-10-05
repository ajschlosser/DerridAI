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
import { ref } from "vue";
import ResearchFilterEditor from "./ResearchFilterEditor.vue";

const accepted = async () => ({
  valid: true,
  fields_referenced: ["work"],
  collection_filter_fields: ["work", "page_start", "speaker"],
  unsupported_fields: [],
  errors: [],
  warnings: [],
});

const meta: Meta<typeof ResearchFilterEditor> = {
  title: "Research/Filter editor",
  component: ResearchFilterEditor,
  parameters: { layout: "padded" },
  args: {
    modelValue: "",
    collection: "derrida_primary",
    fields: ["work", "page_start", "speaker"],
    preview: accepted,
  },
};
export default meta;
type Story = StoryObj<typeof ResearchFilterEditor>;
export const Empty: Story = {};
export const ValidExpression: Story = {
  args: {
    modelValue: 'work = "Of Grammatology" and page_start >= 100 and speaker != "Heidegger"',
  },
};
export const WithDocumentCondition: Story = {
  args: {
    modelValue:
      'work in ("Of Grammatology", "Writing and Difference") and document contains "trace"',
  },
};
export const SyntaxError: Story = {
  args: { modelValue: 'work = "Of Grammatology" and author = 1' },
};
export const ServerRejected: Story = {
  args: {
    modelValue: 'speaker = "Derrida"',
    preview: async () => ({
      valid: false,
      fields_referenced: ["speaker"],
      collection_filter_fields: ["work"],
      unsupported_fields: ["speaker"],
      errors: [{ code: "unknown_field", params: { field: "speaker" } }],
      warnings: [],
    }),
  },
};
export const NoDeclaredFields: Story = { args: { fields: [], modelValue: "" } };

/** Holds its own expression so typing, suggestions and the server check can be exercised. */
export const Interactive: Story = {
  render: (args) => ({
    components: { ResearchFilterEditor },
    setup() {
      const expression = ref("");
      return { args, expression };
    },
    template: '<ResearchFilterEditor v-bind="args" v-model="expression" />',
  }),
};

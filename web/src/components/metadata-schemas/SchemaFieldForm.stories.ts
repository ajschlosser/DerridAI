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
import { blankField, type SchemaField } from "../../api/metadataSchemas";
import SchemaFieldForm from "./SchemaFieldForm.vue";

const field = (over: Partial<SchemaField> = {}): SchemaField => ({
  ...blankField("indexing"),
  name: "characters_present",
  label: "Characters present",
  type: "list",
  ...over,
});

const meta = {
  title: "System/Metadata Schemas/Field form",
  component: SchemaFieldForm,
  args: {
    field: field(),
    groupKeys: ["indexing", "discourse"],
    matchOptions: [{ fieldId: "field-speaker", label: "Speaker" }],
  },
} satisfies Meta<typeof SchemaFieldForm>;
export default meta;
type Story = StoryObj<typeof meta>;

/** No policy of its own: DerridAI's default for the field applies. */
export const DefaultValueMatching: Story = {};

export const NameIdentity: Story = {
  args: {
    field: field({
      equivalence_profile: {
        mode: "entity_name",
        collection_semantics: "set",
        identity_kind: "character",
      },
    }),
  },
};

export const OrderedPhrases: Story = {
  args: {
    field: field({
      name: "motifs",
      label: "Motifs",
      equivalence_profile: {
        mode: "lexical_phrase",
        collection_semantics: "ordered",
        identity_kind: null,
      },
    }),
  },
};

export const FrenchLengthStress: Story = {
  args: {
    field: field({
      equivalence_profile: {
        mode: "lexical_phrase",
        collection_semantics: "set",
        identity_kind: "motif",
      },
    }),
  },
  parameters: { locale: "fr-CA" },
};

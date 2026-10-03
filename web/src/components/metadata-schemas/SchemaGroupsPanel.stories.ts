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
import { blankField, type MetadataSchema } from "../../api/metadataSchemas";
import SchemaGroupsPanel from "./SchemaGroupsPanel.vue";

const draft = (): MetadataSchema => ({
  format_version: 2,
  id: "notes",
  name: "Reading notes",
  description: "",
  groups: [
    {
      key: "discourse",
      label: "Discourse and attribution",
      intro: "Infer only the discourse metadata supported by the record.",
      fields_heading: "Discourse fields",
      notes: ["Preserve uncertainty rather than guessing."],
      trailer: "",
      footer: "Return one assessment for every assessed field.",
    },
    {
      key: "ideas",
      label: "Concepts and themes",
      intro: "Identify concepts and themes supported by the record.",
      fields_heading: "Conceptual fields",
      notes: [],
      trailer: "",
      footer: "Return one assessment for every assessed field.",
    },
  ],
  fields: [
    { ...blankField("discourse"), name: "speaker", label: "Speaker" },
    { ...blankField("ideas"), name: "concepts", label: "Concepts", type: "list" },
  ],
});

const meta = {
  title: "System/Metadata Schemas/Prompt groups",
  component: SchemaGroupsPanel,
  args: { draft: draft(), readonly: false },
} satisfies Meta<typeof SchemaGroupsPanel>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Editable: Story = {};
export const ReadOnly: Story = { args: { readonly: true } };
export const FrenchLengthStress: Story = {
  args: {
    draft: {
      ...draft(),
      groups: [
        {
          ...draft().groups[0],
          label: "Discours, attribution et position du détenteur de l’énoncé",
          fields_heading: "Champs relatifs au discours et à l’attribution",
        },
      ],
    },
  },
  parameters: { locale: "fr-CA" },
};

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
import SchemaFieldsTable from "./SchemaFieldsTable.vue";

const group = {
  key: "discourse",
  label: "Discourse",
  intro: "",
  fields_heading: "",
  notes: [],
  trailer: "",
  footer: "",
};
const draft = (): MetadataSchema => ({
  format_version: 1,
  id: "notes",
  name: "Reading notes",
  description: "",
  groups: [group],
  fields: [
    {
      ...blankField("discourse"),
      name: "mood",
      label: "Mood",
      type: "choice",
      evidence: true,
      review: true,
    },
    { ...blankField("discourse"), name: "themes", label: "Themes", type: "list", assess: true },
  ],
});
const meta = {
  title: "System/Metadata Schemas/Fields",
  component: SchemaFieldsTable,
  args: { draft: draft(), readonly: false },
} satisfies Meta<typeof SchemaFieldsTable>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Editable: Story = {};
export const ReadOnly: Story = { args: { readonly: true } };

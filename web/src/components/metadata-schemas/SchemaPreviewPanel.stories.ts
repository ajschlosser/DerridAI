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
import { blankField, type MetadataSchema, type SchemaPreview } from "../../api/metadataSchemas";
import SchemaPreviewPanel from "./SchemaPreviewPanel.vue";

const draft: MetadataSchema = {
  format_version: 2,
  id: "notes",
  name: "Reading notes",
  description: "",
  groups: [
    {
      key: "discourse",
      label: "Discourse and attribution",
      intro: "Infer only supported discourse metadata.",
      fields_heading: "Fields",
      notes: [],
      trailer: "",
      footer: "Return assessments for assessed fields.",
    },
  ],
  fields: [{ ...blankField("discourse"), name: "speaker", label: "Speaker", evidence: true }],
};

const promptOnly = async (): Promise<SchemaPreview> => ({
  prompt: "SYSTEM\nInfer only the requested fields.\n\nPASSAGE\n…",
  answer_schema: {},
  ran: false,
});

const meta = {
  title: "System/Metadata Schemas/Test schema",
  component: SchemaPreviewPanel,
  args: {
    draft,
    busy: false,
    providerProfiles: [],
    defaultProviderId: "",
    run: promptOnly,
  },
} satisfies Meta<typeof SchemaPreviewPanel>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Ready: Story = {};
export const Busy: Story = { args: { busy: true } };
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};

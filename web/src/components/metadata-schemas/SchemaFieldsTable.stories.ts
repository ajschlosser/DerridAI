/* Copyright 2026 Aaron John Schlosser, PhD. */
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

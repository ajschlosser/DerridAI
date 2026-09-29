/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { defaultDocumentFields, type MetadataSchema } from "../../api/metadataSchemas";
import SchemaDocumentFieldsPanel from "./SchemaDocumentFieldsPanel.vue";

const draft = (): MetadataSchema => ({
  format_version: 2,
  id: "notes",
  name: "Reading notes",
  description: "",
  groups: [],
  fields: [],
  document_fields: defaultDocumentFields(),
});
const meta = {
  title: "System/Metadata Schemas/Document fields",
  component: SchemaDocumentFieldsPanel,
  args: { draft: draft(), readonly: false },
} satisfies Meta<typeof SchemaDocumentFieldsPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Editable: Story = {};
export const ReadOnly: Story = { args: { readonly: true } };

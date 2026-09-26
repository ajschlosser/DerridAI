/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SchemaListTable from "./SchemaListTable.vue";

const items = [
  {
    id: "default",
    name: "DerridAI scholarly default",
    description: "",
    builtin: true,
    field_count: 23,
    groups: ["discourse", "ideas"],
    hash: "a",
    schema_version: "1.0.0",
  },
  {
    id: "notes",
    name: "Reading notes",
    description: "Marginalia fields",
    builtin: false,
    field_count: 5,
    groups: ["discourse"],
    hash: "b",
    schema_version: "1.2.0",
  },
];
const meta = {
  title: "System/Metadata Schemas/List",
  component: SchemaListTable,
  args: { items, selectedId: "notes", unsavedName: "" },
} satisfies Meta<typeof SchemaListTable>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const WithUnsavedDraft: Story = { args: { unsavedName: "New schema" } };

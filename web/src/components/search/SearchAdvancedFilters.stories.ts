/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SearchAdvancedFilters from "./SearchAdvancedFilters.vue";

const meta = {
  title: "Search/Advanced filters",
  component: SearchAdvancedFilters,
  args: {
    filters: [
      {
        id: "f1",
        field: "work",
        field_label: "Work",
        op: "eq",
        op_label: "is",
        value: "Of Grammatology",
      },
    ],
    fields: [
      { key: "work", label: "Work", kind: "text" },
      { key: "speaker", label: "Speaker", kind: "text" },
    ],
    schemas: [
      {
        id: "default",
        name: "Default",
        description: "",
        builtin: true,
        field_count: 12,
        groups: [],
        hash: "h",
      },
    ],
    schemaId: "default",
    associatedSchemaId: "default",
    field: "speaker",
    op: "eq",
    value: "",
    ops: [
      ["eq", "search.op_eq", "is"],
      ["contains", "search.op_contains", "contains"],
    ],
    suggestions: ["Derrida", "Levinas"],
  },
} satisfies Meta<typeof SearchAdvancedFilters>;
export default meta;
type Story = StoryObj<typeof meta>;
export const WithCondition: Story = {};
export const Empty: Story = { args: { filters: [] } };

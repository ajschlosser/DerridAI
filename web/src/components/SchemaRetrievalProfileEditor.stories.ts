/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SchemaRetrievalProfileEditor from "./SchemaRetrievalProfileEditor.vue";

const meta: Meta<typeof SchemaRetrievalProfileEditor> = {
  title: "Metadata Schemas/Retrieval Policy",
  component: SchemaRetrievalProfileEditor,
  args: {
    modelValue: {
      enabled: true,
      max_items: 6,
      min_similarity: 0.2,
      include_corrections: true,
      include_confirmed_absence: true,
      max_corrections: 2,
      match_field_ids: ["field-genre"],
    },
    matchOptions: [
      { fieldId: "core.discourse_role", label: "Discourse role" },
      { fieldId: "field-genre", label: "Genre" },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof SchemaRetrievalProfileEditor>;
export const Default: Story = {};
export const NoOtherFields: Story = { args: { matchOptions: [] } };

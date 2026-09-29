/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusMissingDocumentFields from "./CorpusMissingDocumentFields.vue";

const meta = {
  title: "Corpus Builder/Missing document fields",
  component: CorpusMissingDocumentFields,
  args: {
    modelValue: {},
    fields: [
      { name: "document_author", requiredFor: ["evidence", "publication"] },
      { name: "title", requiredFor: ["evidence", "publication"] },
    ],
    disabled: false,
  },
} satisfies Meta<typeof CorpusMissingDocumentFields>;
export default meta;
type Story = StoryObj<typeof meta>;
export const AuthorAndTitleMissing: Story = {};
export const Disabled: Story = { args: { disabled: true } };

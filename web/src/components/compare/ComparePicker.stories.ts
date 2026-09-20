/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ComparePicker from "./ComparePicker.vue";

const meta = {
  title: "Compare/Picker",
  component: ComparePicker,
  args: {
    modelValue: "f::0",
    options: [
      {value: "f::0", label: "tab.jsonl · r-a · Glas"},
      {value: "f::1", label: "tab.jsonl · r-b · Voice and Phenomenon"},
    ],
    label: "Find a loaded record",
    placeholder: "Type record ID, work, author, or file…",
    selectedHint: "Selected · tab.jsonl · r-a · Glas",
    emptyHint: "Start typing to search loaded records.",
    noMatches: "No matching records.",
    clearLabel: "Clear",
  },
} satisfies Meta<typeof ComparePicker>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Empty: Story = {args: {modelValue: "", options: [], emptyHint: "Load JSONL files or browse the corpus database first."}};

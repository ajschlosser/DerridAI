// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiTagPicker from "./UiTagPicker.vue";

const meta = {
  title: "UI/Tag Picker",
  component: UiTagPicker,
  args: {
    modelValue: ["NOUN", "PROPN"],
    options: [
      "ADJ",
      "ADP",
      "ADV",
      "AUX",
      "CCONJ",
      "DET",
      "INTJ",
      "NOUN",
      "NUM",
      "PART",
      "PRON",
      "PROPN",
      "PUNCT",
      "SCONJ",
      "SYM",
      "VERB",
      "X",
    ],
    label: "POS tags",
    placeholder: "Search POS tags…",
    removeLabel: "Remove {value}",
  },
} satisfies Meta<typeof UiTagPicker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SelectedTags: Story = {};
export const Empty: Story = { args: { modelValue: [] } };
export const Disabled: Story = { args: { disabled: true } };

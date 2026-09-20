/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorksLibraryCard from "./WorksLibraryCard.vue";
import type { WorksItem } from "../../types/works";

const work: WorksItem = {
  work: "Adieu to Emmanuel Levinas",
  count: 318,
  review: 4,
  annotations: 2,
  files: ["adieu.jsonl"],
  authors: ["Jacques Derrida"],
  years: ["1999"],
  cover: "",
  citation: "Derrida, Jacques. Adieu to Emmanuel Levinas. Stanford University Press, 1999.",
  year_label: "1999",
  subtitle: "",
  publisher: {field_label: "Publisher", value: "Stanford University Press", mixed: false, unique_count: 0},
  translator: {field_label: "Translator", value: "Pascale-Anne Brault", mixed: false, unique_count: 0},
  metadata: [],
  status: {kind: "synced", label: "Synced"},
  insights: [],
};

const meta = {
  title: "Works/Library Card",
  component: WorksLibraryCard,
  args: {work, selected: false, canSync: true, syncDisabledReason: ""},
} satisfies Meta<typeof WorksLibraryCard>;
export default meta;
type Story = StoryObj<typeof WorksLibraryCard>;
export const Default: Story = {};
export const Selected: Story = {args: {selected: true}};
export const NeedsReview: Story = {args: {work: {...work, review: 12, status: {kind: "changed", label: "Pending changes"}}}};

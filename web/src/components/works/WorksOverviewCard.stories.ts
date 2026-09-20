/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorksOverviewCard from "./WorksOverviewCard.vue";
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
  subtitle: "Jacques Derrida · 1999 · Stanford University Press",
  publisher: {field_label: "Publisher", value: "Stanford University Press", mixed: false, unique_count: 0},
  translator: {field_label: "Translator", value: "Pascale-Anne Brault", mixed: false, unique_count: 0},
  metadata: [
    {field: "document_author", field_label: "Document author", value: "Jacques Derrida", mixed: false, unique_count: 0},
    {field: "publisher", field_label: "Publisher", value: "Stanford University Press", mixed: false, unique_count: 0},
    {field: "publication_year", field_label: "Publication year", value: "1999", mixed: false, unique_count: 0},
  ],
  status: {kind: "synced", label: "Synced"},
  insights: [
    {id: "topics", field: "topics", title: "Top 5 topics in the work", heading: "Top 5 topics", type: "bars", values: [{key: "ethics", value: 18}, {key: "hospitality", value: 11}]},
    {id: "roles", field: "discourse_role", title: "Top discourse roles as percentage of recorded roles", heading: "Top discourse roles as percentage of recorded roles", type: "pie", values: [{key: "analysis", value: 12}, {key: "quotation", value: 5}]},
  ],
};

const meta = {
  title: "Works/Overview Card",
  component: WorksOverviewCard,
  args: {work, mode: "admin" as const, citationLabel: "Full citation"},
} satisfies Meta<typeof WorksOverviewCard>;
export default meta;
type Story = StoryObj<typeof WorksOverviewCard>;
export const Admin: Story = {};
export const Researcher: Story = {args: {mode: "researcher"}};

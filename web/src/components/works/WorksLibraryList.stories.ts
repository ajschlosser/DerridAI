/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { WorksLibraryItem } from "../../types/works";
import WorksLibraryList from "./WorksLibraryList.vue";

function biblio(label: string, value = "") {
  return { field_label: label, value, mixed: false, unique_count: 0 };
}

const works: WorksLibraryItem[] = [
  {
    work: "Adieu to Emmanuel Levinas",
    count: 318,
    review: 4,
    annotations: 2,
    files: ["adieu.jsonl"],
    authors: ["Jane Author"],
    years: ["1999"],
    cover: "",
    year_label: "1999",
    subtitle: "",
    publisher: biblio("Publisher", "Stanford University Press"),
    translator: biblio("Translator", "Pascale-Anne Brault"),
    status: { kind: "changed", label: "Pending changes" },
  },
  {
    work: "Of Grammatology",
    count: 912,
    review: 0,
    annotations: 7,
    files: ["grammatology.jsonl"],
    authors: ["Jane Author"],
    years: ["1976"],
    cover: "",
    year_label: "1976",
    subtitle: "",
    publisher: biblio("Publisher", "Johns Hopkins University Press"),
    translator: biblio("Translator", "Gayatri Chakravorty Spivak"),
    status: { kind: "synced", label: "Synced" },
  },
  {
    work: "Introduction to Edmund Husserl’s Origin of Geometry: A Translation with Extended Commentary on the Problem of Ideal Objectivity",
    count: 144,
    review: 12,
    annotations: 0,
    files: ["origin-geometry.jsonl"],
    authors: ["Jane Author"],
    years: ["1962"],
    cover: "",
    year_label: "1962",
    subtitle: "",
    publisher: biblio("Publisher"),
    translator: biblio("Translator"),
    status: { kind: "absent", label: "Not in DB" },
  },
];

const meta = {
  title: "Works/Library List",
  component: WorksLibraryList,
  args: {
    works,
    selectedWork: "Of Grammatology",
    mode: "admin",
    canSync: true,
    syncDisabledReason: "",
  },
} satisfies Meta<typeof WorksLibraryList>;

export default meta;
type Story = StoryObj<typeof WorksLibraryList>;

export const Admin: Story = {};
export const Researcher: Story = {
  args: {
    mode: "researcher",
    selectedWork: "",
  },
};
export const DatabaseUnavailable: Story = {
  args: {
    canSync: false,
    syncDisabledReason: "No search index is available.",
    works: works.map((work) => ({
      ...work,
      status: { kind: "none", label: "No search index" },
    })),
  },
};

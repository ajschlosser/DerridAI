/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3";
import CreateSiteDialog from "./CreateSiteDialog.vue";

const meta = {
  title: "Works/CreateSiteDialog",
  component: CreateSiteDialog,
  args: {
    storeName: "derrida-primary",
    works: [
      {
        work: "Glas",
        count: 128,
        review: 0,
        annotations: 4,
        files: ["glas.jsonl"],
        authors: ["Jacques Derrida"],
        years: ["1974"],
        cover: "",
        citation: "Derrida, Jacques. Glas.",
        year_label: "1974",
        subtitle: "Jacques Derrida · 1974",
        publisher: { field_label: "Publisher", value: "Galilée", mixed: false, unique_count: 1 },
        translator: { field_label: "Translator", value: "", mixed: false, unique_count: 0 },
        metadata: [],
        status: { kind: "synced", label: "Synced" },
        insights: [],
      },
      {
        work: "Of Grammatology",
        count: 214,
        review: 0,
        annotations: 2,
        files: ["grammatology.jsonl"],
        authors: ["Jacques Derrida"],
        years: ["1967"],
        cover: "",
        citation: "Derrida, Jacques. Of Grammatology.",
        year_label: "1967",
        subtitle: "Jacques Derrida · 1967",
        publisher: { field_label: "Publisher", value: "", mixed: false, unique_count: 0 },
        translator: { field_label: "Translator", value: "", mixed: false, unique_count: 0 },
        metadata: [],
        status: { kind: "synced", label: "Synced" },
        insights: [],
      },
    ],
    initialWork: "Glas",
    languages: [
      { code: "en-US", name: "English", flag: "🇺🇸" },
      { code: "fr-CA", name: "Français", flag: "🇨🇦" },
    ],
    providerProfiles: [
      {
        id: "openai-main",
        name: "OpenAI-compatible lab",
        type: "openai",
        base_url: "https://models.example.edu/v1",
        model: "gpt-oss:20b",
      },
    ],
    busy: false,
    error: "",
  },
} satisfies Meta<typeof CreateSiteDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Busy: Story = {
  args: { busy: true },
};

export const Error: Story = {
  args: { error: "The selected work is not indexed in this corpus database." },
};

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
        authors: ["Jacques Derrida"],
        year_label: "1974",
      },
      {
        work: "Of Grammatology",
        count: 214,
        authors: ["Jacques Derrida"],
        year_label: "1967",
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

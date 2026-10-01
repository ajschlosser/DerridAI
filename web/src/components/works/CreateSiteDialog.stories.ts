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
    transformersRuntime: {
      version: "4.3.0",
      cached: false,
      download_bytes: 14_871_000,
      inline_bytes: 5_700_000,
    },
    busy: false,
    error: "",
  },
} satisfies Meta<typeof CreateSiteDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const RuntimeCached: Story = {
  args: {
    transformersRuntime: {
      version: "4.3.0",
      cached: true,
      download_bytes: 14_871_000,
      inline_bytes: 5_700_000,
    },
  },
};

export const RuntimeInfoUnavailable: Story = {
  args: { transformersRuntime: undefined },
};

export const Busy: Story = {
  args: { busy: true },
};

export const Error: Story = {
  args: { error: "The selected work is not indexed in this corpus database." },
};

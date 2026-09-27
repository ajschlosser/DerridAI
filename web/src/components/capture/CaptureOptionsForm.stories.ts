/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CaptureOptionsForm from "./CaptureOptionsForm.vue";

const providerInfo = [
  {
    provider: "gutenberg" as const,
    catalogue_ready: true,
    catalogue_refreshed_at: "2026-09-27T00:00:00Z",
    local_collection_ready: false,
  },
  {
    provider: "wikisource" as const,
    projects: [
      { code: "en", name: "English" },
      { code: "fr", name: "French" },
      { code: "de", name: "German" },
      { code: "es", name: "Spanish" },
    ],
    projects_authoritative: true,
  },
];

const meta = {
  title: "Corpus Builder/Capture/Options",
  component: CaptureOptionsForm,
  args: {
    providers: ["gutenberg", "wikisource"],
    includes: {
      authored: true,
      translations: true,
      translator: false,
      editor: false,
      other: false,
    },
    languages: null,
    providerInfo,
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof CaptureOptionsForm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllLanguages: Story = {};

export const FrenchAndGerman: Story = {
  args: { languages: ["fr", "de"] },
};

export const ContributorRoles: Story = {
  args: {
    includes: {
      authored: true,
      translations: false,
      translator: true,
      editor: true,
      other: true,
    },
  },
};

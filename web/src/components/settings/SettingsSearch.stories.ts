/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import SettingsSearch from "./SettingsSearch.vue";
import type { SettingsSearchHit } from "./SettingsSearch.vue";

const hits: SettingsSearchHit[] = [
  { id: "rag-k", section: "retrieval", label: "Retrieval k", group: "Vector stores and retrieval" },
  { id: "theme", section: "workspace", label: "Color theme", group: "Workspace and appearance" },
];

const meta = {
  title: "Settings/Search",
  component: SettingsSearch,
  render: (args) => ({
    components: { SettingsSearch },
    setup: () => {
      const query = ref(args.modelValue);
      return { args, query };
    },
    template: '<div style="max-width:520px"><SettingsSearch v-bind="args" v-model="query" /></div>',
  }),
  args: {
    modelValue: "retriev",
    results: hits,
    label: "Search settings",
    placeholder: "Find a setting",
    noResults: "No settings match that search.",
    resultCount: "2 matching settings",
  },
} satisfies Meta<typeof SettingsSearch>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Matches: Story = {};
export const Empty: Story = {
  args: { modelValue: "xyzzy", results: [], resultCount: "0 matching settings" },
};
export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    label: "Rechercher dans les paramètres",
    placeholder: "Trouver un paramètre",
    noResults: "Aucun paramètre ne correspond à cette recherche.",
    resultCount: "2 paramètres correspondants",
    results: [
      {
        id: "rag-k",
        section: "retrieval",
        label: "k de repérage",
        group: "Magasins vectoriels et repérage",
      },
    ],
  },
};

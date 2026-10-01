/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorksCorpusContext from "./WorksCorpusContext.vue";

const meta = {
  title: "Works/Corpus Context",
  component: WorksCorpusContext,
  args: {
    mode: "admin",
    stores: [
      { name: "derrida_primary", count: 3102 },
      { name: "derrida_secondary", count: 880 },
    ],
    activeStore: "derrida_primary",
    activeStoreCount: 3102,
    sourceFileCount: 4,
    totalRecords: 3218,
    indexFreshness: {
      state: "stale",
      totalRecords: 3218,
      currentRecords: 3102,
      changedRecords: 84,
      presentRecords: 0,
      absentRecords: 32,
      unknownRecords: 0,
      unavailableRecords: 0,
    },
    storesEmptyLabel: "No search indexes available",
    dbUnavailableReason: "",
    canSyncAll: true,
    syncAllDisabledReason: "",
  },
} satisfies Meta<typeof WorksCorpusContext>;
export default meta;
type Story = StoryObj<typeof WorksCorpusContext>;
export const Admin: Story = {};
export const NoDatabase: Story = {
  args: {
    stores: [],
    activeStore: "",
    activeStoreCount: 0,
    indexFreshness: {
      state: "unavailable",
      totalRecords: 3218,
      currentRecords: 0,
      changedRecords: 0,
      presentRecords: 0,
      absentRecords: 0,
      unknownRecords: 0,
      unavailableRecords: 3218,
    },
    canSyncAll: false,
    dbUnavailableReason: "No corpus database is available.",
    syncAllDisabledReason: "No corpus database is available.",
  },
};
export const Researcher: Story = { args: { mode: "researcher" } };

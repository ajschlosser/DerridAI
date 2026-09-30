/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import LibraryCatalogueStatus from "./LibraryCatalogueStatus.vue";

const status = (
  archive: { status: string; bytes_done: number; total_bytes?: number; error?: string },
  catalogue = { status: "ready", item_count: 70000 },
) => ({ ready: false, search_ready: catalogue.status === "ready", catalogue, archive });

const meta = {
  title: "Corpus Builder/Library/Catalogue Status",
  component: LibraryCatalogueStatus,
  args: {
    status: status({ status: "idle", bytes_done: 0 }),
    catalogueReady: true,
    disabled: false,
    busy: "",
  },
} satisfies Meta<typeof LibraryCatalogueStatus>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CollectionNeeded: Story = {};
export const CatalogueNeeded: Story = {
  args: {
    status: status({ status: "idle", bytes_done: 0 }, { status: "missing", item_count: 0 }),
    catalogueReady: false,
  },
};
export const Downloading: Story = {
  args: {
    status: status({ status: "downloading", bytes_done: 4.2e9, total_bytes: 9.8e9 }),
  },
};
export const FailedWithPartialDownload: Story = {
  args: {
    status: status({
      status: "error",
      bytes_done: 2.1e9,
      total_bytes: 9.8e9,
      error: "Connection reset",
    }),
  },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };

/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusLibrarySearch from "./CorpusLibrarySearch.vue";

const ready = {
  ready: true,
  search_ready: true,
  catalogue: { status: "ready", item_count: 74213 },
  archive: { status: "ready", bytes_done: 1, total_bytes: 1 },
};
const wikisource = (title: string, snippet: string, words: number) => ({
  source: "wikisource" as const,
  language: "fr",
  title,
  page_id: title.length,
  snippet,
  word_count: words,
  url: `https://fr.wikisource.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`,
});

const meta = {
  title: "Corpus Builder/Source/Library Search",
  component: CorpusLibrarySearch,
  args: {
    query: "",
    language: "fr",
    gutenbergStatus: ready,
    gutenbergHits: [],
    wikisourceHits: [],
  },
} satisfies Meta<typeof CorpusLibrarySearch>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Idle: Story = {};

export const GutenbergResults: Story = {
  args: {
    query: "Rousseau",
    searched: { gutenberg: "Rousseau", wikisource: "" },
    gutenbergHits: [
      {
        etext_id: 46333,
        title: "The Social Contract & Discourses",
        author: "Jean-Jacques Rousseau",
        language: "en",
      },
      {
        etext_id: 5427,
        title: "Émile ou de l'éducation",
        author: "Jean-Jacques Rousseau",
        language: "fr",
      },
    ],
    importing: "gutenberg:46333",
  },
};

export const CollectionDownloading: Story = {
  args: {
    query: "Rousseau",
    searched: { gutenberg: "Rousseau", wikisource: "" },
    gutenbergStatus: {
      ready: false,
      search_ready: true,
      catalogue: { status: "ready", item_count: 74213 },
      archive: { status: "downloading", bytes_done: 4_200_000_000, total_bytes: 9_800_000_000 },
    },
    gutenbergHits: [
      {
        etext_id: 46333,
        title: "The Social Contract & Discourses",
        author: "Jean-Jacques Rousseau",
        language: "en",
      },
    ],
  },
};

export const NoResults: Story = {
  args: { query: "zzzz", searched: { gutenberg: "zzzz", wikisource: "" } },
};

export const SearchFailed: Story = {
  args: { query: "Rousseau", error: "Wikisource search failed: HTTP 503" },
};

// Wikisource opens on its own tab inside the component; this story's data is for that tab.
export const WikisourceWorks: Story = {
  args: {
    query: "Rousseau",
    searched: { gutenberg: "", wikisource: "Rousseau" },
    wikisourceHits: [
      wikisource(
        "Du contrat social/Édition 1762/Livre I",
        "L’homme est né libre, et partout il est dans les fers.",
        4120,
      ),
      wikisource(
        "Du contrat social/Édition 1762/Livre II",
        "La première et la plus importante conséquence…",
        6023,
      ),
      wikisource("Les Confessions (Rousseau)/Livre I", "Je forme une entreprise…", 15210),
    ],
  },
};

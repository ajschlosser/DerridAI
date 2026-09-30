/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { groupWikisourceHits } from "../../features/corpus-builder/domain/wikisourceGroups";
import LibraryResultList from "./LibraryResultList.vue";

const wikisource = (title: string, words: number) => ({
  source: "wikisource" as const,
  title,
  page_id: 1,
  snippet: `Extrait de ${title}`,
  word_count: words,
  url: `https://fr.wikisource.org/wiki/${encodeURIComponent(title)}`,
});

const meta = {
  title: "Corpus Builder/Library/Result List",
  component: LibraryResultList,
  args: {
    library: "gutenberg",
    gutenbergHits: [
      { etext_id: 1234, title: "Meno", author: "Plato", language: "en" },
      { etext_id: 5678, title: "Discours de la méthode", author: "Descartes", language: "fr" },
    ],
    workGroups: groupWikisourceHits([
      wikisource("De la grammatologie/Livre I", 4120),
      wikisource("De la grammatologie/Livre II", 6023),
      wikisource("La Voix et le phénomène", 900),
    ]),
    searching: false,
    collectionReady: true,
    disabled: false,
    importing: "",
    languageName: (code: string) => (code === "fr" ? "Français" : "English"),
  },
} satisfies Meta<typeof LibraryResultList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Gutenberg: Story = {};
export const Wikisource: Story = { args: { library: "wikisource" } };
export const Importing: Story = { args: { importing: "gutenberg:1234" } };
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };

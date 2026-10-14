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
import type { LanguagePack } from "../../api/documentNlp";
import DocumentNlpLanguagePacks from "./DocumentNlpLanguagePacks.vue";

const pack = (overrides: Partial<LanguagePack>): LanguagePack => ({
  pack_id: "booknlp-en-small",
  language: "en",
  engine: "booknlp",
  label: "BookNLP English (small models, CPU-friendly)",
  source_url: "https://github.com/booknlp/booknlp",
  license: "MIT",
  origin: "builtin",
  files: [],
  installable: true,
  installed: false,
  download_bytes: 160398571,
  worker_bundled: true,
  ...overrides,
});

const catalog: LanguagePack[] = [
  pack({
    pack_id: "spacy-it-md",
    language: "it",
    engine: "spacy",
    tier: "md",
    label: "spaCy it_core_news_md 3.8.0",
    source_url: "https://spacy.io/models/it#it_core_news_md",
    license: "",
    download_bytes: 42_000_000,
  }),
  pack({
    pack_id: "spacy-ja-md",
    language: "ja",
    engine: "spacy",
    tier: "md",
    label: "spaCy ja_core_news_md 3.8.0",
    source_url: "https://spacy.io/models/ja#ja_core_news_md",
    license: "",
    installable: false,
    missing_requirements: ["sudachipy", "sudachidict-core"],
    download_bytes: 42_000_000,
  }),
  pack({
    pack_id: "spacy-xx-sm",
    language: "xx",
    engine: "spacy",
    tier: "sm",
    label: "spaCy xx_ent_wiki_sm 3.8.0",
    source_url: "https://spacy.io/models/xx#xx_ent_wiki_sm",
    license: "",
    installed: true,
    download_bytes: 11_000_000,
  }),
  pack({
    pack_id: "booknlp-en-big",
    label: "BookNLP English (big models)",
    download_bytes: 1196238139,
  }),
  pack({ installed: true, installed_at: "2026-09-28T12:00:00Z" }),
  pack({
    pack_id: "spacy-la-latincy-sm",
    language: "la",
    engine: "spacy",
    tier: "sm",
    label: "LatinCy la_core_web_sm 3.9.8",
    source_url: "https://huggingface.co/latincy/la_core_web_sm",
    license: "MIT",
    note: "Bundled Latin pipeline for classical, medieval, and scholarly Latin text.",
    bundled: true,
    installable: false,
    installed: true,
    worker_bundled: true,
    download_bytes: 0,
  }),
];

/** Serve a fixed catalog so each story shows one state without a backend. */
function withCatalog(packs: LanguagePack[]) {
  return () => {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ packs, models_dir: "/data/models/booknlp" }), {
        headers: { "Content-Type": "application/json" },
      });
    return { template: "<story />" };
  };
}

const meta = {
  title: "Settings/Language Packs",
  component: DocumentNlpLanguagePacks,
  decorators: [withCatalog(catalog)],
} satisfies Meta<typeof DocumentNlpLanguagePacks>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Catalog: Story = {};
export const Installing: Story = {
  decorators: [
    withCatalog([
      pack({
        pack_id: "booknlp-en-big",
        active_job: {
          id: "nlp-pack-1",
          status: "running",
          completed: 420_000_000,
          total: 1_196_238_139,
        },
      }),
      ...catalog.slice(5),
    ]),
  ],
};
export const French: Story = { parameters: { locale: "fr-CA" } };

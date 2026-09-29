/* Copyright 2026 Aaron John Schlosser, PhD. */
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
    pack_id: "propp-fr",
    language: "fr",
    engine: "propp-fr",
    label: "Propp (French literary NER and coreference)",
    source_url: "https://github.com/lattice-8094/propp",
    license: "MIT (library), Apache-2.0 (models)",
    note: "Propp is a separate pipeline, not BookNLP; it needs its own worker.",
    installable: false,
    worker_bundled: false,
    download_bytes: 167206700,
  }),
  pack({
    pack_id: "llpro-de",
    language: "de",
    engine: "llpro",
    label: "LLpro (German literary texts)",
    source_url: "https://github.com/cophi-wue/LLpro",
    license: "GPL-3.0",
    installable: false,
    worker_bundled: false,
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

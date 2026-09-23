import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSourceIngest from "./CorpusSourceIngest.vue";
import type { GutenbergHit, PdfAsset } from "../api/pdfCorpus";

const asset = {
  asset_id: "pdf-hospitality",
  sha256: "abcdef1234567890abcdef",
  filename: "Of Hospitality.txt",
  created_at: "2026-09-23T08:00:00Z",
  page_count: 2,
  block_count: 14,
  ocr_pages: 0,
  warnings: [],
  metadata: {},
  media_kind: "text",
  deterministic_checked_at: "2026-09-23T08:00:01Z",
  initial_metadata: { title: "Of Hospitality", document_author: "Jacques Derrida", speaker: "Jacques Derrida" },
} as PdfAsset;

const hits: GutenbergHit[] = [
  { etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" },
  { etext_id: 2701, title: "Moby Dick; Or, The Whale", author: "Herman Melville", language: "en" },
];

const meta = {
  title: "Corpus Builder/Source/Ingest",
  component: CorpusSourceIngest,
  args: { assets: [asset], assetId: "", illegibility: 20, hits: [], selectedAsset: null, disabled: false, busy: "" },
} satisfies Meta<typeof CorpusSourceIngest>;

export default meta;
type Story = StoryObj<typeof meta>;

export const BeforeFileSelection: Story = {};
export const GutenbergResults: Story = { args: { hits, gutenbergQuery: "austen" } };
export const DeterministicCheck: Story = { args: { assetId: asset.asset_id, selectedAsset: asset, illegibility: 0 } };
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: { assetId: asset.asset_id, selectedAsset: { ...asset, filename: "De l’hospitalité — édition commentée.txt" }, hits, illegibility: 80 },
};

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { PdfAsset } from "../api/corpus";
import CorpusUnitPolicy from "./CorpusUnitPolicy.vue";

const asset = {
  asset_id: "pdf-essay",
  sha256: "abcdef1234567890abcdef",
  filename: "Of Hospitality.txt",
  created_at: "2026-09-23T08:00:00Z",
  page_count: 4,
  block_count: 42,
  ocr_pages: 0,
  warnings: [],
  metadata: {},
  media_kind: "text",
} as PdfAsset;

// The preview is fetched from the API; without a backend the story shows its error state.
const meta = {
  title: "Corpus Builder/Structure/Unit Policy",
  component: CorpusUnitPolicy,
  args: { asset, disabled: false, busy: false },
} satisfies Meta<typeof CorpusUnitPolicy>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const SentenceApplied: Story = {
  args: { asset: { ...asset, asset_id: "pdf-essay-s", unit_policy: { mode: "sentence" } } },
};
export const LockedDuringBuild: Story = { args: { disabled: true } };

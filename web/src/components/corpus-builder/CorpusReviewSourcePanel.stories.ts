import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import CorpusReviewSourcePanel from "./CorpusReviewSourcePanel.vue";

const blocks: SourceBlock[] = [
  {
    block_id: "b1",
    page: 12,
    type: "paragraph",
    text: "For Levinas, responsibility precedes freedom.",
    bbox: [0, 0, 1, 1],
    extraction_method: "native",
    confidence: 1,
  },
  { block_id: "b2", page: 12, type: "paragraph", text: "Derrida reads this against Husserl." },
];

const meta = {
  title: "Corpus Builder/Review/Source Panel",
  component: CorpusReviewSourcePanel,
  args: {
    record: {
      record_id: "r1",
      text: "For Levinas, responsibility precedes freedom.",
      text_length: 44,
      source_block_ids: ["b1"],
      source_spans: [],
      source_extracted_text: "For Levinas, responsibility precedes freedom.",
    } as CorpusRecord,
    showPdfExplorer: false,
    page: 12,
    pageCount: 200,
    pageWidth: 0,
    pageHeight: 0,
    pageBlocks: [],
    evidenceIds: ["b1"],
    zoomable: false,
    canPreviousPage: true,
    canNextPage: true,
    canMergePrevious: true,
    canMergeNext: true,
    profiles: [],
    providerProfileId: "",
    modelOverride: "",
    concurrencyRisk: false,
    activeRequests: 0,
    concurrencyLimit: 1,
    blocks,
    evidenceBlockIds: new Set(["b1"]),
    paginatedSource: true,
    selectedEvidenceField: "speaker",
    busy: false,
  },
} satisfies Meta<typeof CorpusReviewSourcePanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Busy: Story = { args: { busy: true } };

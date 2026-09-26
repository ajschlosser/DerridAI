import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusRecord, SourceBlock } from "../../api/corpus";
import CorpusReviewSourcePanel from "./CorpusReviewSourcePanel.vue";

const record: CorpusRecord = {
  record_id: "record-1",
  text: "A representative record with source context.",
  text_length: 44,
  source_block_ids: ["block-1", "block-2"],
  source_spans: [],
  source_extracted_text:
    "Original extracted source text before any human correction or cleanup.",
};

const blocks: SourceBlock[] = [
  {
    block_id: "block-1",
    page: 12,
    bbox: [],
    type: "paragraph",
    text: "Derrida writes that a cited position must remain distinguishable from the position attributed to another speaker.",
    extraction_method: "pdf_text",
    confidence: 0.99,
  },
  {
    block_id: "block-2",
    page: 12,
    bbox: [],
    type: "paragraph",
    text: "The next source block continues the passage and can be split independently.",
    extraction_method: "pdf_text",
    confidence: 0.98,
  },
];

const meta = {
  title: "Corpus Builder/Review/Source Panel",
  component: CorpusReviewSourcePanel,
  args: {
    record,
    workspaceMode: "record",
    mediaKind: "pdf",
    audioUrl: "",
    imageUrl: "",
    showPdfExplorer: true,
    pdfUrl: "",
    page: 12,
    pageCount: 20,
    pageWidth: 612,
    pageHeight: 792,
    pageBlocks: blocks,
    visibleBlocks: blocks,
    evidenceIds: ["block-1"],
    evidenceBlockIds: new Set(["block-1"]),
    selectedEvidenceField: "speaker",
    paginatedSource: true,
    canPreviousSourcePage: true,
    canNextSourcePage: true,
    canMergePrevious: true,
    canMergeNext: true,
    profiles: [
      {
        id: "local",
        name: "Local Ollama",
        type: "ollama",
        model: "gemma4:e2b",
        max_concurrent_requests: 1,
      },
    ],
    providerProfileId: "local",
    modelOverride: "",
    activeRequests: 0,
    disabled: false,
  },
} satisfies Meta<typeof CorpusReviewSourcePanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RecordInspector: Story = {};

export const SourceWorkspace: Story = {
  args: {
    workspaceMode: "source",
  },
};

export const BusyWithConcurrentLocalModel: Story = {
  args: {
    activeRequests: 1,
    disabled: true,
  },
};

export const NoEvidenceFieldSelected: Story = {
  args: {
    selectedEvidenceField: "",
    evidenceBlockIds: new Set(),
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};

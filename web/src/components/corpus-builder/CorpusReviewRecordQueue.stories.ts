import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusRecord } from "../../api/corpus";
import CorpusReviewRecordQueue from "./CorpusReviewRecordQueue.vue";

function record(
  recordId: string,
  reviewState: string,
  overrides: Partial<CorpusRecord> = {},
): CorpusRecord {
  return {
    record_id: recordId,
    text: "A representative record for queue presentation.",
    text_length: 47,
    inline_citation: "Derrida, p. 12",
    source_block_ids: ["block-1"],
    source_spans: [],
    review_state: reviewState,
    ...overrides,
  };
}

const records = [
  record("record-ready", "ready", { metadata_enrichment_finished: true }),
  record("record-metadata", "metadata", {
    review_issue_codes: ["metadata", "source"],
  }),
  record("record-accepted", "accepted", { accepted: true }),
  record("record-rejected", "rejected", { rejected: true }),
];

const meta = {
  title: "Corpus Builder/Review/Record Queue",
  component: CorpusReviewRecordQueue,
  args: {
    records,
    recordTotal: records.length,
    selectedRecordId: "record-metadata",
    selectedReviewIds: new Set(["record-metadata"]),
    allVisibleSelected: false,
    loading: false,
    hydrated: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusReviewRecordQueue>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MixedStates: Story = {};

export const SourceWarning: Story = {
  args: {
    records: [
      record("record-source", "source", {
        source_quality_issues: [{ code: "ocr_noise", severity: "warning" }],
      }),
    ],
    recordTotal: 1,
    selectedRecordId: "record-source",
  },
};

export const Empty: Story = {
  args: {
    records: [],
    recordTotal: 0,
    selectedRecordId: "",
    selectedReviewIds: new Set(),
  },
};

export const Loading: Story = {
  args: {
    records: [],
    recordTotal: 0,
    selectedRecordId: "",
    selectedReviewIds: new Set(),
    loading: true,
    hydrated: false,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};

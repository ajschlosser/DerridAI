import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewRecordPane from "./CorpusReviewRecordPane.vue";

const record = {
  record_id: "rec_0184",
  inline_citation: "(Author 1967, p. 12)",
  text: "Le texte précède le commentaire.",
  text_length: 27,
  text_review_status: "unreviewed",
  review_reason: "Quotation attribution needs review.",
  source_block_ids: [],
  source_spans: [],
};

const meta = {
  title: "Corpus Builder/Review/Record Pane",
  component: CorpusReviewRecordPane,
  args: {
    record: record as never,
    buildId: "build-1",
    visible: true,
    queueCollapsed: false,
    editing: false,
    busy: false,
    locked: false,
    activitySummary: "",
    popout: null,
    textDraft: "",
    showContext: false,
    resolveSource: false,
  },
} satisfies Meta<typeof CorpusReviewRecordPane>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Reading: Story = {};
export const Editing: Story = {
  args: { editing: true, textDraft: "Le texte précède le commentaire." },
};
export const NothingSelected: Story = { args: { record: null } };

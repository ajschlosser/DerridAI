import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusRecordFocusReview from "./CorpusRecordFocusReview.vue";
const record = {
  record_id: "record-00014",
  text: "A representative passage under review. The focus view keeps the proposed scholarly unit visually dominant while its attribution and discourse data remain immediately available for verification.",
  text_length: 188,
  page_start: 22,
  page_end: 23,
  pdf_pages: [24, 25],
  source_block_ids: ["p00024-b0003", "p00024-b0004"],
  source_spans: [],
  needs_review: true,
  review_reason: "Boundary requires human review.",
  review_disposition: "pending" as const,
  record_revision: 2,
  speaker: "Jacques Derrida",
  position_holder: "Jacques Derrida",
  stance: "qualified assertion",
  discourse_role: "analysis",
  proposition_status: "asserted",
  topics: ["hospitality", "cosmopolitanism"],
  concepts: ["unconditional hospitality"],
  metadata_guidance_matches: {
    persons: [{ term: "Jacques Derrida", occurrences: 1 }],
    concepts: [{ term: "hospitality", occurrences: 2 }],
  },
  metadata_evidence: {
    speaker: {
      block_ids: ["p00024-b0003"],
      confidence: 0.97,
      reason: "Explicit first-person continuation.",
    },
    region_type: {
      block_ids: ["p00024-b0003"],
      confidence: 0.98,
      reason: "Substantive essay body.",
    },
    primary_text: {
      block_ids: ["p00024-b0003"],
      confidence: 0.99,
      reason: "Substantive argument.",
    },
    discourse_role: {
      block_ids: ["p00024-b0004"],
      confidence: 0.91,
      reason: "Analytical exposition.",
    },
  },
  metadata_field_status: {
    region_type: {
      status: "model_inferred",
      method: "llm",
      confidence: 0.98,
      reason: "Substantive essay body.",
    },
    primary_text: {
      status: "deterministic",
      method: "manifest_page_range",
      confidence: 1,
      reason: "Inside main-text range.",
    },
    discourse_role: {
      status: "model_inferred",
      method: "llm",
      confidence: 0.91,
      reason: "Analytical exposition.",
    },
  },
  region_type: "main_text",
  primary_text: true,
};
const meta = {
  title: "Corpus Builder/Review/Focus View",
  component: CorpusRecordFocusReview,
  args: {
    canMergePrevious: true,
    canMergeNext: true,
    canHistoryBack: true,
    canHistoryForward: true,
    canPreviousRecord: true,
    canNextRecord: true,
    record,
    sourceBlocks: [
      {
        block_id: "p00024-b0003",
        page: 24,
        bbox: [10, 20, 400, 140],
        type: "paragraph",
        text: "A representative passage under review.",
        extraction_method: "native",
        confidence: 0.99,
      },
      {
        block_id: "p00024-b0004",
        page: 24,
        bbox: [10, 150, 400, 260],
        type: "paragraph",
        text: "The focus view keeps the proposed scholarly unit visually dominant.",
        extraction_method: "native",
        confidence: 0.99,
      },
    ],
  },
} satisfies Meta<typeof CorpusRecordFocusReview>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Pending: Story = {};
export const Rejected: Story = {
  args: {
    record: {
      ...record,
      review_disposition: "rejected",
      rejected: true,
      needs_review: false,
      review_reason: "Rejected during human review.",
    },
  },
};
export const LongMetadata: Story = {
  args: {
    record: {
      ...record,
      text: (record.text + " ").repeat(8),
      text_length: 1504,
      quoted_author: ["Emmanuel Levinas", "Immanuel Kant"],
      works_referenced: ["Totality and Infinity", "Perpetual Peace"],
      persons: ["Levinas", "Kant", "Derrida"],
    },
  },
};
export const HumanCorrectedSourceIssue: Story = {
  args: {
    canAccept: false,
    record: {
      ...record,
      text: "A human-corrected passage under review. The immutable extracted source remains available in the Source tab.",
      text_review_status: "human_corrected",
      source_extracted_text: "A human-cor�rected passage under review.",
      source_quality_issues: [
        {
          code: "replacement_character",
          severity: "minor",
          pages: [24],
          message: "A replacement character remains in the original PDF text layer.",
        },
      ],
      metadata_field_status: {
        ...record.metadata_field_status,
        document_author: {
          status: "inherited",
          method: "document_manifest",
          confidence: 1,
          reason: "Inherited from document manifest.",
        },
        speaker: {
          status: "human_confirmed",
          method: "human",
          confidence: 1,
          reason: "Confirmed during review.",
        },
      },
      document_author: "Jacques Derrida",
    },
  },
};
export const IllegibleOcr: Story = {
  args: {
    canAccept: false,
    record: {
      ...record,
      text: "rouge, c'est le res.c;ic, rornrne le t•ail:lit justement K]ossowski. C111.11.31.CS de rockers Oil (11.:CHeS sc. hrisent",
      text_length: 118,
      needs_review: true,
      review_reason:
        "Source extraction issue: inspect the affected source, correct the reviewed record text when appropriate, or rebuild/re-extract the source before acceptance.",
      source_quality_issues: [
        {
          code: "illegible_text",
          severity: "blocking",
          pages: [24],
          noise: 66,
          message: "Extracted text does not look like words in a writing system.",
        },
      ],
      text_noise: {
        score: 66,
        deterministic_score: 66,
        raster_score: null,
        threshold: 45,
        unusable: true,
        reasons: ["interior_punct", "letter_digit_mix", "high_text_noise"],
        method: "deterministic",
      },
    },
  },
};
export const PixelatedScan: Story = {
  args: {
    canAccept: false,
    record: {
      ...record,
      needs_review: true,
      review_reason:
        "Source extraction issue: inspect the affected source, correct the reviewed record text when appropriate, or rebuild/re-extract the source before acceptance.",
      source_quality_issues: [
        {
          code: "low_raster_quality",
          severity: "blocking",
          pages: [24],
          message: "Embedded page image resolution is too low to trust as a scholarly scan.",
        },
      ],
      text_noise: {
        score: 80,
        deterministic_score: 80,
        raster_score: 80,
        threshold: 45,
        unusable: true,
        reasons: ["low_raster_quality", "high_text_noise"],
        method: "deterministic",
      },
    },
  },
};
export const FrenchLengthStress: Story = {
  args: {
    record: {
      ...record,
      review_reason:
        "La délimitation de cette fiche exige une vérification humaine parce que la transition entre l’analyse principale, la citation rapportée et le commentaire éditorial demeure ambiguë.",
      document_title: "Cosmopolites de tous les pays, encore un effort !",
      publisher: "Presses universitaires — édition critique et annotations complémentaires",
    },
  },
};

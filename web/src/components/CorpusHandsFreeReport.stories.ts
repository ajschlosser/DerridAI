import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusHandsFreeReport from "./CorpusHandsFreeReport.vue";

const policy = {
  enabled: true,
  passes: 2,
  min_confidence: 0.8,
  unresolved: "leave" as const,
  accept_records: true,
  publish: false,
};

const meta = {
  title: "Corpus Builder/Review/Hands-Free Report",
  component: CorpusHandsFreeReport,
  args: {
    report: {
      records: 84,
      accepted: 79,
      fields_filled: 216,
      left_for_review: 5,
      passes_run: 2,
      ran_at: "2026-09-25T12:00:00Z",
      exceptions: [
        { record_id: "record-0017", reasons: ["position holder remains unresolved"] },
        { record_id: "record-0049", reasons: ["source evidence requires review"] },
      ],
      notes: ["Deterministic and previously human-owned fields were preserved."],
      policy,
    },
  },
} satisfies Meta<typeof CorpusHandsFreeReport>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ExceptionsRemaining: Story = {};

export const Published: Story = {
  args: {
    report: {
      records: 42,
      accepted: 42,
      fields_filled: 138,
      left_for_review: 0,
      passes_run: 1,
      ran_at: "2026-09-25T12:00:00Z",
      exceptions: [],
      notes: ["No review exceptions remained after validation."],
      policy: { ...policy, publish: true },
      published: true,
    },
  },
};

export const ManyExceptions: Story = {
  args: {
    report: {
      records: 60,
      accepted: 41,
      fields_filled: 130,
      left_for_review: 19,
      passes_run: 3,
      ran_at: "2026-09-25T12:00:00Z",
      exceptions: Array.from({ length: 12 }, (_, index) => ({
        record_id: `record-${String(index + 1).padStart(4, "0")}`,
        reasons: ["metadata ambiguity", "evidence needs review"],
      })),
      notes: ["The remaining records were left unresolved instead of receiving forced values."],
      policy,
    },
  },
};

export const FrenchLongText: Story = {
  args: {
    report: {
      records: 18,
      accepted: 14,
      fields_filled: 57,
      left_for_review: 4,
      passes_run: 2,
      ran_at: "2026-09-25T12:00:00Z",
      exceptions: [
        {
          record_id: "record-texte-philosophique-0007",
          reasons: [
            "L’attribution de la position reste ambiguë et les preuves disponibles ne permettent pas de trancher sans révision humaine.",
          ],
        },
      ],
      notes: [
        "Les valeurs non établies ont été conservées comme non résolues plutôt que transformées en certitudes artificielles.",
      ],
      policy,
    },
  },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 420px"><story /></div>',
    }),
  ],
};

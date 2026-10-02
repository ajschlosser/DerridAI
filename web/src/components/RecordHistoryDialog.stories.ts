// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordHistoryDialog from "./RecordHistoryDialog.vue";
import { openRecordHistoryDialog } from "../composables/recordHistoryDialog";

const versions = [
  {
    label: "Original",
    record: { work: "Of Grammatology", year: "1967", text: "Il n'y a pas de hors-texte." },
  },
  {
    label: "Change 1",
    timestamp: "2026-09-30T14:00:00Z",
    source: "manual",
    record: { work: "Of Grammatology", year: "1976", text: "Il n'y a pas de hors-texte." },
  },
];

const meta = {
  title: "Records/Record History Dialog",
  component: RecordHistoryDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { RecordHistoryDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><RecordHistoryDialog /></div>`,
    methods: {
      open() {
        openRecordHistoryDialog({
          recordId: "rec-0001",
          versions: () => versions,
          changedFields: (a, b) => Object.keys(b).filter((k) => a[k] !== b[k]),
          fieldLabel: (field) => field,
          formatValue: (value) => JSON.stringify(value),
          formatTimestamp: (value) => value,
          restore: async () => false,
          restoreOriginal: async () => false,
          clear: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof RecordHistoryDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TwoVersions: Story = {};

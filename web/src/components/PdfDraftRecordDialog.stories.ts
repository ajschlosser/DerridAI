// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PdfDraftRecordDialog from "./PdfDraftRecordDialog.vue";
import { openPdfDraftRecordDialog } from "../composables/pdfDraftRecordDialog";

const meta = {
  title: "Jobs/PDF Draft Record Dialog",
  component: PdfDraftRecordDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { PdfDraftRecordDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><PdfDraftRecordDialog /></div>`,
    methods: {
      open() {
        openPdfDraftRecordDialog({
          title: "Of Grammatology",
          page: 158,
          recordJson: '{\n  "text": "There is nothing outside the text."\n}',
          files: [{ id: "f1", name: "grammatology.jsonl", count: 120 }],
          stores: [{ id: "derrida", name: "derrida", count: 4200 }],
          save: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof PdfDraftRecordDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithDestinations: Story = {};

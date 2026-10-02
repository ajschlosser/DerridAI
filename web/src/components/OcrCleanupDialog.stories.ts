// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import OcrCleanupDialog from "./OcrCleanupDialog.vue";
import { openOcrCleanupDialog } from "../composables/ocrCleanupDialog";

const meta = {
  title: "Records/OCR Cleanup Dialog",
  component: OcrCleanupDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { OcrCleanupDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><OcrCleanupDialog /></div>`,
    methods: {
      open() {
        openOcrCleanupDialog({
          active: { name: "of-grammatology.jsonl", recordCount: 1280 },
          selectedCount: 0,
          reviewCount: 42,
          allCount: 2220,
          fileCount: 2,
          choose: async () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof OcrCleanupDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NothingSelected: Story = {};

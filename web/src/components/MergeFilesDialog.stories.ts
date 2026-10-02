// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MergeFilesDialog from "./MergeFilesDialog.vue";
import { openMergeFilesDialog } from "../composables/mergeFilesDialog";

const meta = {
  title: "Records/Merge Files Dialog",
  component: MergeFilesDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { MergeFilesDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><MergeFilesDialog /></div>`,
    methods: {
      open() {
        openMergeFilesDialog({
          files: [
            { id: "a", name: "of-grammatology.jsonl", recordCount: 1280 },
            { id: "b", name: "writing-and-difference.jsonl", recordCount: 940 },
          ],
          defaultName: "derridai-merged.jsonl",
          merge: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof MergeFilesDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TwoTabs: Story = {};

// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MixedWorkValuesDialog from "./MixedWorkValuesDialog.vue";
import { openMixedWorkValuesDialog } from "../composables/mixedWorkValuesDialog";

const meta = {
  title: "Works/Mixed Work Values Dialog",
  component: MixedWorkValuesDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { MixedWorkValuesDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><MixedWorkValuesDialog /></div>`,
    methods: {
      open() {
        openMixedWorkValuesDialog({
          work: "Of Grammatology",
          fieldLabel: "Publication year",
          recordCount: 12,
          values: [
            { text: "1967", files: ["grammatology-1.jsonl", "grammatology-2.jsonl"], count: 8 },
            {
              text: "1976",
              files: ["grammatology-3.jsonl", "a.jsonl", "b.jsonl", "c.jsonl"],
              count: 3,
            },
            { text: null, files: ["grammatology-4.jsonl"], count: 1 },
          ],
        });
      },
    },
  }),
} satisfies Meta<typeof MixedWorkValuesDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Variants: Story = {};

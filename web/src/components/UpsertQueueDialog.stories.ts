// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UpsertQueueDialog from "./UpsertQueueDialog.vue";
import { openUpsertQueueDialog } from "../composables/upsertQueueDialog";

const meta = {
  title: "Records/Upsert Queue Dialog",
  component: UpsertQueueDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { UpsertQueueDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><UpsertQueueDialog /></div>`,
    methods: {
      open() {
        let items = [
          {
            key: "f1::0",
            recordId: "rec-0001",
            source: "Of Grammatology · grammatology.jsonl",
            status: { kind: "changed", label: "Changed locally" },
            changes: [
              {
                field: "Speaker",
                source: "manual",
                when: "2026-10-02 14:00",
                oldValue: '"Derrida"',
                newValue: '"Rousseau"',
              },
            ],
          },
        ];
        openUpsertQueueDialog({
          store: "derrida",
          items: () => items,
          remove: (key) => (items = items.filter((item) => item.key !== key)),
          sync: async () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof UpsertQueueDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const OneChangedRecord: Story = {};

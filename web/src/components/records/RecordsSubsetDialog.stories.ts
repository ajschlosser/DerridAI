/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { onMounted, ref } from "vue";
import RecordsSubsetDialog from "./RecordsSubsetDialog.vue";

const meta = {
  title: "Records/Subset Dialog",
  component: RecordsSubsetDialog,
} satisfies Meta<typeof RecordsSubsetDialog>;
export default meta;
type Story = StoryObj<typeof RecordsSubsetDialog>;

const records = [
  {
    record_id: "glas-1",
    document_author: "Jacques Derrida",
    work: "Glas",
    language: "fr",
    topics: ["Hegel", "mourning"],
  },
  {
    record_id: "glas-2",
    document_author: "Jacques Derrida",
    work: "Glas",
    language: "fr",
    topics: ["Genet"],
  },
  {
    record_id: "margins-1",
    document_author: "Jacques Derrida",
    work: "Margins of Philosophy",
    language: "en",
    topics: ["différance"],
  },
  {
    record_id: "allegories-1",
    document_author: "Paul de Man",
    work: "Allegories of Reading",
    language: "en",
    topics: ["rhetoric"],
  },
];
const props = {
  sources: [
    { id: "active", name: "derrida-primary.jsonl", count: 4 },
    { id: "all", name: "", count: 4 },
    { id: "f1", name: "derrida-primary.jsonl", count: 4 },
  ],
  fields: [
    { key: "document_author", label: "Document author" },
    { key: "language", label: "Language" },
    { key: "topics", label: "Topics" },
    { key: "work", label: "Work" },
  ],
  defaultName: "derrida-primary-subset.jsonl",
  recordsFor: () => records,
};

export const Open: Story = {
  render: () => ({
    components: { RecordsSubsetDialog },
    setup() {
      const dialog = ref<{ open: () => void } | null>(null);
      onMounted(() => dialog.value?.open());
      return { dialog, props };
    },
    template: `<RecordsSubsetDialog ref="dialog" v-bind="props" />`,
  }),
};

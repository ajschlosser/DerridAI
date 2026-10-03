/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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

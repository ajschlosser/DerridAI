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
import UiTableColumnsDialog from "./UiTableColumnsDialog.vue";

const meta = {
  title: "UI/Table Columns Dialog",
  component: UiTableColumnsDialog,
} satisfies Meta<typeof UiTableColumnsDialog>;
export default meta;
type Story = StoryObj<typeof UiTableColumnsDialog>;

const available = [
  { key: "__db_status", label: "DB status" },
  { key: "work", label: "Work" },
  { key: "page_start", label: "Page start" },
  { key: "needs_review", label: "Needs review" },
  { key: "text", label: "Extracted text" },
  { key: "speaker", label: "Speaker" },
  { key: "record_id", label: "Record ID" },
];

const render = (withWidths: boolean) => () => ({
  components: { UiTableColumnsDialog },
  setup() {
    const selected = ref(["__db_status", "work", "text"]);
    const widths = ref(withWidths ? { __db_status: 12, work: 23, text: 65 } : null);
    const dialog = ref<{ open: () => void } | null>(null);
    onMounted(() => dialog.value?.open());
    return { available, selected, widths, dialog };
  },
  template: withWidths
    ? `<UiTableColumnsDialog ref="dialog" :available="available" v-model="selected" v-model:widths="widths" />`
    : `<UiTableColumnsDialog ref="dialog" :available="available" v-model="selected" />`,
});

/** Records: choose, order and size the columns. */
export const WithWidths: Story = { render: render(true) };
/** Search: choose and order only; the table sizes its own columns. */
export const ChooseAndOrder: Story = { render: render(false) };

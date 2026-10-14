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
import WorkMetadataEditorDialog from "./WorkMetadataEditorDialog.vue";
import { openWorkMetadataEditorDialog } from "../composables/workMetadataEditor";

const meta = {
  title: "Works/Work Metadata Editor Dialog",
  component: WorkMetadataEditorDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { WorkMetadataEditorDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><WorkMetadataEditorDialog /></div>`,
    methods: {
      open() {
        openWorkMetadataEditorDialog({
          work: "Of Grammatology",
          recordCount: 128,
          fileCount: 2,
          fields: [
            {
              field: "publisher",
              label: "Publisher",
              kind: "text",
              mixed: true,
              mixedCount: 2,
              initial: "",
            },
            {
              field: "publication_year",
              label: "Publication year",
              kind: "number",
              mixed: false,
              mixedCount: 0,
              initial: "1967",
            },
            {
              field: "document_is_translation",
              label: "Is translation",
              kind: "boolean",
              mixed: false,
              mixedCount: 0,
              initial: "false",
            },
            {
              field: "full_citation",
              label: "Full citation",
              kind: "textarea",
              mixed: false,
              mixedCount: 0,
              initial: "",
            },
          ],
          inspectMixed: () => undefined,
          apply: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof WorkMetadataEditorDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MixedAndSingleValues: Story = {};

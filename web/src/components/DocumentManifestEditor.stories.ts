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
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
const meta: Meta<typeof DocumentManifestEditor> = {
  title: "Corpus Builder/Metadata/Document Manifest Editor",
  component: DocumentManifestEditor,
  args: {
    manifest: {
      title: "Rogues",
      document_author: "Jacques Derrida",
      translator: "Pascale-Anne Brault and Michael Naas",
      publication_year: 2005,
      language: "English",
      original_language: "French",
      main_text_start_page: 11,
      main_text_end_page: 191,
    },
  },
};
export default meta;
type Story = StoryObj<typeof DocumentManifestEditor>;
export const Default: Story = {};
export const ReadOnlyWhileBuilding: Story = { args: { disabled: true } };

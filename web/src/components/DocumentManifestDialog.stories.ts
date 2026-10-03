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
import DocumentManifestDialog from "./DocumentManifestDialog.vue";

const manifest = {
  title: "On Cosmopolitanism and Forgiveness",
  document_author: "Jacques Derrida",
  translator: "Mark Dooley; Michael Hughes",
  publisher: "Routledge",
  publication_year: 2001,
  document_language: "en",
  original_language: "fr",
};
const meta: Meta<typeof DocumentManifestDialog> = {
  title: "Corpus Builder/Review/Document Metadata Dialog",
  component: DocumentManifestDialog,
  args: { manifest },
};
export default meta;
type Story = StoryObj<typeof DocumentManifestDialog>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };

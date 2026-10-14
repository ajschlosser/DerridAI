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
import CorpusSetupDocumentMetadata from "./CorpusSetupDocumentMetadata.vue";

const meta = {
  title: "Corpus Builder/Setup/Early Manifest",
  component: CorpusSetupDocumentMetadata,
  args: {
    mediaKind: "text",
    missingRequiredCount: 0,
    reviewerOverrideCount: 0,
    manifest: {
      title: "Of Grammatology",
      document_author: "Jacques Derrida",
      translator: "Gayatri Chakravorty Spivak",
      publication_year: 1976,
      language: "en",
      original_language: "fr",
      document_is_translation: true,
      deterministic_ingest: {
        applied: {
          title: {
            value: "Of Grammatology",
            derivation: "computed",
            method: "title_page",
            confidence: 0.99,
          },
          document_author: {
            value: "Jacques Derrida",
            derivation: "nlp_derived",
            method: "title_page_entities",
            confidence: 0.96,
          },
        },
      },
    },
  },
} satisfies Meta<typeof CorpusSetupDocumentMetadata>;

export default meta;
type Story = StoryObj<typeof meta>;

export const EditableBeforeBuild: Story = {};

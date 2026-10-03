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
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";

const meta = {
  title: "Corpus Builder/Setup/Build Plan",
  component: CorpusBuildReadiness,
  args: {
    sourceFilename: "On Cosmopolitanism and Forgiveness.pdf",
    pageCount: 75,
    blockCount: 307,
    structureSummary: "Main text PDF 9 → printed p. 1",
    providerLabel: "Local Ollama",
    modelLabel: "qwen3.5:4b",
    enrichmentMode: "deep",
    targetChars: 1750,
    toleranceChars: 200,
    contextSafe: true,
    activeBuildCount: 0,
    canStart: true,
  },
} satisfies Meta<typeof CorpusBuildReadiness>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ready: Story = {};
export const NoSource: Story = {
  args: {
    sourceFilename: "",
    pageCount: 0,
    blockCount: 0,
    canStart: false,
  },
};
export const Warning: Story = {
  args: {
    issues: [
      {
        id: "structure_review",
        section: "structure",
        severity: "warning",
        message: "Review document structure before building.",
      },
    ],
  },
};
export const NeedsAttention: Story = {
  args: {
    canStart: false,
    contextSafe: false,
    issues: [
      {
        id: "context_unsafe",
        section: "advanced",
        severity: "blocking",
        message: "Context budget is too small for the selected settings.",
      },
      {
        id: "structure_review",
        section: "structure",
        severity: "warning",
        message: "Review document structure before building.",
      },
    ],
  },
};
export const ConcurrentBuild: Story = { args: { activeBuildCount: 2 } };

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    sourceFilename:
      "Jacques Derrida — Cosmopolites de tous les pays, encore un effort ! — édition critique et annotée.pdf",
    schemaLabel:
      "Schéma de métadonnées pour l’analyse discursive, l’attribution et l’indexation sémantique",
    providerLabel: "Fournisseur local de recherche",
    modelLabel: "modèle-expérimental-à-contexte-étendu",
    issues: [
      {
        id: "structure_review",
        section: "structure",
        severity: "warning",
        message:
          "Révisez la structure du document avant la construction afin de confirmer la correspondance des pages imprimées.",
      },
    ],
  },
};

export const Narrow: Story = {
  parameters: {
    viewport: { defaultViewport: "mobile1" },
  },
};

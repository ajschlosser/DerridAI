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
import type { MetadataPrecedents } from "../api/corpus";
import CorpusFieldPrecedents from "./CorpusFieldPrecedents.vue";

const precedents: MetadataPrecedents = {
  field: "mood",
  record_id: "r-7",
  mode: "semantic",
  fallback_reason: "",
  items: [
    {
      exemplar_id: "mex-1",
      record_id: "r-2",
      record_revision: 3,
      value: "calm",
      similarity: 0.86,
      evidence_bound: true,
      evidence: "The letter proceeds without haste, each clause set down evenly.",
      match: { tier: "matched", fields: ["genre"] },
      candidate_source_units: [
        { block_id: "b-2", score: 0.78, method: "precedent-semantic-v1", page: 14 },
        { block_id: "b-3", score: 0.52, method: "precedent-semantic-v1", page: 15 },
      ],
    },
    {
      exemplar_id: "mex-2",
      record_id: "r-4",
      record_revision: 1,
      value: "calm",
      kind: "correction",
      rejected_value: "angry",
      similarity: 0.74,
      evidence_bound: true,
      evidence: "He repeats the question, but the tone stays measured.",
    },
    {
      record_id: "r-5",
      record_revision: 2,
      value: "angry",
      similarity: 0.41,
      evidence_bound: false,
      excerpt: "An older decision recorded before reviewed evidence was kept.",
    },
  ],
};

const meta: Meta<typeof CorpusFieldPrecedents> = {
  title: "Corpus Builder/Review/Field Precedents",
  component: CorpusFieldPrecedents,
  args: {
    buildId: "build-1",
    recordId: "r-7",
    field: "mood",
    fieldLabel: "Mood",
    load: async () => precedents,
  },
};
export default meta;
type Story = StoryObj<typeof CorpusFieldPrecedents>;
export const Collapsed: Story = {};
export const Empty: Story = {
  args: { load: async () => ({ ...precedents, mode: "none", items: [] }) },
};
export const LexicalFallback: Story = {
  args: {
    load: async () => ({
      ...precedents,
      mode: "lexical",
      fallback_reason: "embedding service offline",
    }),
  },
};
export const LoadError: Story = {
  args: {
    load: async () => {
      throw new Error("Corpus record not found");
    },
  },
};
export const Loading: Story = {
  args: { load: () => new Promise(() => {}) },
};
export const Absence: Story = {
  args: {
    load: async () => ({
      ...precedents,
      items: [
        {
          exemplar_id: "mex-9",
          record_id: "r-9",
          record_revision: 2,
          value: null,
          kind: "absence",
          similarity: 0.63,
          evidence_bound: true,
          evidence: "The preface names no date of composition.",
        },
      ],
    }),
  },
};

/** Kept from the last enrichment: the count shows on the closed toggle, and one precedent has since changed. */
export const KeptFromEnrichment: Story = {
  args: {
    preloaded: {
      ...precedents,
      source: "enrichment",
      computed_at: "2026-09-20T14:05:00Z",
      stale_count: 1,
    },
    sourceBlockIds: ["b-1", "b-2", "b-3"],
  },
};

/** Audio: candidates are located by time range, not page. */
export const TimedSource: Story = {
  args: {
    preloaded: {
      ...precedents,
      items: [
        {
          ...precedents.items[0],
          candidate_source_units: [
            { block_id: "seg-4", score: 0.66, method: "precedent-lexical-v1", start: 62, end: 75 },
          ],
        },
      ],
    },
  },
};

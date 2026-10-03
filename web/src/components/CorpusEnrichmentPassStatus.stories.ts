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
import CorpusEnrichmentPassStatus from "./CorpusEnrichmentPassStatus.vue";
import type { CorpusBuild } from "../api/pdfCorpus";
const build = (operation: Record<string, unknown>) =>
  ({
    build_id: "demo",
    metadata_operation: {
      operation_id: "op-1",
      kind: "metadata_enrichment_rerun",
      records_total: 60,
      passes_requested: 3,
      ...operation,
    },
  }) as unknown as CorpusBuild;
const meta = {
  title: "Corpus Builder/Status/Enrichment Pass Status",
  component: CorpusEnrichmentPassStatus,
} satisfies Meta<typeof CorpusEnrichmentPassStatus>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Running: Story = {
  args: {
    build: build({
      state: "running",
      current_pass: 2,
      records_processed: 90,
      pass_results: [{ pass: 1, records_processed: 60, fields_added: 12 }],
      fields_replaced: 4,
      fields_kept: 2,
      records_disputed: 3,
    }),
  },
};
export const CompletedConverged: Story = {
  args: {
    build: build({
      state: "completed",
      passes_completed: 2,
      converged: true,
      records_processed: 120,
      pass_results: [
        { pass: 1, records_processed: 60, fields_added: 12 },
        { pass: 2, records_processed: 60, fields_added: 0 },
      ],
      fields_replaced: 4,
      fields_kept: 2,
      records_disputed: 3,
    }),
  },
};
export const Stopped: Story = {
  args: {
    build: build({
      state: "cancelled",
      passes_completed: 1,
      records_processed: 60,
      pass_results: [{ pass: 1, records_processed: 60, fields_added: 12 }],
    }),
  },
};
export const IdleAfterInitial: Story = {
  args: {
    build: {
      build_id: "demo",
      status: "awaiting_review",
      stage: "review",
      record_count: 60,
    } as unknown as CorpusBuild,
  },
};
export const Failed: Story = {
  args: { build: build({ state: "failed", error: "Provider profile is unreachable." }) },
};

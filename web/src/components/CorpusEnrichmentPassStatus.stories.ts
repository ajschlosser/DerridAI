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

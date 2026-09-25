import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusMetadataLiveStatus from "./CorpusMetadataLiveStatus.vue";

const build = {
  build_id: "build-1",
  asset_id: "asset-1",
  source_filename: "On Cosmopolitanism and Forgiveness.pdf",
  source_sha256: "abc",
  status: "running",
  stage: "enriching",
  progress: 0.52,
  created_at: new Date().toISOString(),
  record_count: 11,
  needs_review_count: 1,
  accepted_count: 0,
  profile_id: "derrida-scholarly-v12",
  metadata_enrichment_total: 11,
  metadata_concurrency: 3,
  metadata_tasks_total: 33,
  metadata_tasks_completed: 7,
  metadata_tasks_failed: 1,
  metadata_tasks_running: 3,
  metadata_tasks_queued: 22,
  metadata_last_progress_at: new Date().toISOString(),
  metadata_active_tasks: [
    {
      record_id: "derrida-cosmopoli-00001",
      task: "quotation",
      started_at: new Date().toISOString(),
    },
    {
      record_id: "derrida-cosmopoli-00002",
      task: "discourse",
      started_at: new Date().toISOString(),
    },
  ],
};
const meta = {
  title: "Corpus Builder/Status/Metadata Live Status",
  component: CorpusMetadataLiveStatus,
  args: { build },
} satisfies Meta<typeof CorpusMetadataLiveStatus>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Running: Story = {};
export const PartialFailure: Story = {
  args: {
    build: {
      ...build,
      metadata_tasks_completed: 18,
      metadata_tasks_failed: 3,
      metadata_tasks_running: 2,
      metadata_tasks_queued: 10,
    },
  },
};
export const Stalled: Story = {
  args: {
    build: {
      ...build,
      metadata_last_progress_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    },
  },
};
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    build: {
      ...build,
      source_filename: "Jacques Derrida — Cosmopolites de tous les pays, encore un effort !.pdf",
    },
  },
};

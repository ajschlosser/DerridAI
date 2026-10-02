import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildWorkspace from "./CorpusBuildWorkspace.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture supplies only the fields the workspace reads.
const build: any = {
  build_id: "build-live-handoff",
  source_filename: "Of Grammatology.pdf",
  status: "running",
  stage: "enriching",
  progress: 0.58,
  record_count: 327,
  needs_review_count: 17,
  metadata_tasks_total: 981,
  metadata_tasks_completed: 552,
  metadata_tasks_running: 3,
  metadata_tasks_queued: 426,
  metadata_active_tasks: [{ record_id: "record-184", task: "quotation" }],
  build_events: [
    { at: "2026-10-01T18:00:00Z", stage: "preparing", status: "running", progress: 0.02 },
    {
      at: "2026-10-01T18:03:00Z",
      stage: "constructing_records",
      status: "running",
      progress: 0.36,
    },
    { at: "2026-10-01T18:08:00Z", stage: "enriching", status: "running", progress: 0.58 },
  ],
};

const meta = {
  title: "Corpus Builder/Build/Workspace",
  component: CorpusBuildWorkspace,
  args: {
    build,
    running: true,
    canResume: false,
    hasRecordTopology: true,
    readyCount: 36,
    preparingCount: 274,
    attentionCount: 17,
    awaitingManifestReview: false,
    retryingSegmentation: false,
    segmentationNeedsReview: false,
    contextSafe: true,
    providerLabel: "Local Ollama",
    modelLabel: "qwen3.5:4b",
  },
} satisfies Meta<typeof CorpusBuildWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProgressiveEnrichment: Story = {};

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildDiagnostics from "./CorpusBuildDiagnostics.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture supplies only the fields diagnostics read.
const build: any = {
  build_id: "build-42",
  source_sha256: "0123456789abcdef",
  status: "awaiting_review",
  stage: "review",
  progress: 1,
  metadata_schema_version: "1.4.0",
  segmentation_prompt_version: "derrida-scholarly-v12",
  build_events: [
    { at: "2026-09-25T18:01:00Z", stage: "preparing", status: "running", progress: 0 },
  ],
};

const meta = {
  title: "Corpus Builder/Build/Diagnostics",
  component: CorpusBuildDiagnostics,
  args: {
    build,
    modelLabel: "qwen3.5:4b",
    runGuidance: [
      {
        field: "discourse_role",
        label: "Discourse role",
        instructions: "Prefer the narrower role.",
        lookFor: ["objection"],
      },
    ],
  },
} satisfies Meta<typeof CorpusBuildDiagnostics>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Collapsed: Story = {};

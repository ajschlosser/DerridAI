/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineBenchmarkCaseList from "./PipelineBenchmarkCaseList.vue";
import type { ResearchPipelineBenchmarkCase } from "../../types/pipelines";

const item = (id: string, version: number): ResearchPipelineBenchmarkCase => ({
  case_id: id,
  version,
  prompt: "What is the trace?",
  source_collection: "primary_corpus",
  corpus_snapshot: { fingerprint: "a".repeat(64), collections: [], limitations: [] },
  created_at: "2026-09-29T20:00:00Z",
});

const meta = {
  title: "Pipelines/Benchmark Case List",
  component: PipelineBenchmarkCaseList,
  args: {
    cases: [item("trace-definition-001", 3), item("evidence-recovery-002", 1)],
    selectedKey: "trace-definition-001@3",
  },
} satisfies Meta<typeof PipelineBenchmarkCaseList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = { args: { cases: [], selectedKey: "" } };

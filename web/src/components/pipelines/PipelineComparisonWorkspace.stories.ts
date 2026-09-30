/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineComparisonWorkspace from "./PipelineComparisonWorkspace.vue";
import type { PipelineDefinition } from "../../types/pipelines";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [
      {
        id: "query",
        strategy: "query.research_decompose",
        enabled: true,
        config: {},
        next: ["dense"],
      },
      {
        id: "dense",
        strategy: "retrieve.chroma_similarity",
        enabled: true,
        config: { fetch_k: 500 },
        next: ["provenance"],
      },
      {
        id: "provenance",
        strategy: "validate.provenance",
        enabled: true,
        config: {},
        next: ["pack"],
      },
      {
        id: "pack",
        strategy: "pack.evidence_context",
        enabled: true,
        config: {},
        next: ["generate"],
      },
      {
        id: "generate",
        strategy: "llm.generate_answer",
        enabled: true,
        config: {},
        next: [],
      },
    ],
    built_in: true,
    runtime_support: { supported: true, adapter: "research" },
  },
  {
    pipeline_id: "research.balanced",
    version: 1,
    name: "Research — balanced",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["query"],
    stages: [
      {
        id: "query",
        strategy: "query.research_decompose",
        enabled: true,
        config: {},
        next: ["dense"],
      },
      {
        id: "dense",
        strategy: "retrieve.chroma_similarity",
        enabled: true,
        config: { fetch_k: 300 },
        next: ["provenance"],
      },
      {
        id: "provenance",
        strategy: "validate.provenance",
        enabled: true,
        config: {},
        next: ["pack"],
      },
      {
        id: "pack",
        strategy: "pack.evidence_context",
        enabled: true,
        config: {},
        next: ["generate"],
      },
      {
        id: "generate",
        strategy: "llm.generate_answer",
        enabled: true,
        config: {},
        next: [],
      },
    ],
    built_in: true,
    runtime_support: { supported: true, adapter: "research" },
  },
];

const meta = {
  title: "Pipelines/Comparison Workspace",
  component: PipelineComparisonWorkspace,
  args: { pipelines },
} satisfies Meta<typeof PipelineComparisonWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

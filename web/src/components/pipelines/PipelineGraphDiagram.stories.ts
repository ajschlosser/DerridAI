/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import { contractStrategies } from "./fixtures/pipelineCatalogContract";
import type { PipelineStage } from "../../types/pipelines";

const stage = (id: string, strategy: string, next: string[] = []): PipelineStage => ({
  id,
  strategy,
  enabled: true,
  config: {},
  next,
});

const stages: PipelineStage[] = [
  stage("dense", "retrieve.chroma_similarity", ["lexical"]),
  stage("lexical", "retrieve.lexical_bm25", ["pick"]),
  stage("pick", "select.top_k"),
];

const meta = {
  title: "Pipelines/Graph Diagram",
  component: PipelineGraphDiagram,
  args: {
    stages,
    entryStageIds: ["dense"],
    strategies: contractStrategies,
    title: "Pipeline diagram",
    description: "Focus or hover a stage to see the data type its connections carry.",
    showInspector: false,
  },
} satisfies Meta<typeof PipelineGraphDiagram>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Plain: Story = {};

/** `dense → lexical` only runs the first stage ahead of a binding; it carries no data. */
export const OrderingOnlyEdge: Story = {
  args: { orderingEdges: [{ from: "dense", to: "lexical" }] },
};

/** Parallel fallbacks and a skip connection must remain individually visible. */
export const MultipleRoutes: Story = {
  args: {
    stages: [
      {
        ...stage("dense", "retrieve.chroma_similarity", ["lexical", "pick"]),
        on_empty: "lexical",
        on_timeout: "lexical",
        on_error: "pick",
      },
      stage("lexical", "retrieve.lexical_bm25", ["pick"]),
      stage("pick", "select.top_k"),
    ],
  },
};

const longId = "review_" + "source_provenance_and_attribution_".repeat(18);
export const DenseLongLabels: Story = {
  args: {
    stages: [
      {
        ...stage(longId, "retrieve.chroma_similarity", ["a", "b", "c", "d", "e", "f", "g"]),
        on_empty: "g",
        on_error: "g",
        on_timeout: "g",
        on_unavailable: "g",
      },
      ...["a", "b", "c", "d", "e", "f"].map((id) => ({
        ...stage(id, "retrieve.lexical_bm25", ["g"]),
        on_empty: "g",
      })),
      stage("g", "select.top_k"),
    ],
    entryStageIds: [longId],
    badges: {
      [longId]: {
        text: "A long translated explanation of the stage's provenance checks. ".repeat(8),
        tone: "warn",
      },
    },
  },
};

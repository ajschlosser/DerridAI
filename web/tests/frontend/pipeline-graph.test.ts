/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";

import { configurationForTrace, layoutPipelineDiagram } from "../../src/domain/pipelineGraph";
import type {
  PipelineDefinition,
  PipelineRunTrace,
  PipelineStage,
} from "../../src/types/pipelines";

const stages: PipelineStage[] = [
  {
    id: "dense",
    strategy: "retrieve.chroma_similarity",
    enabled: true,
    config: {},
    next: ["rerank"],
    on_empty: "lexical",
  },
  {
    id: "lexical",
    strategy: "retrieve.lexical_bm25",
    enabled: true,
    config: {},
    next: ["rerank"],
  },
  {
    id: "rerank",
    strategy: "rerank.cross_encoder",
    enabled: true,
    config: {},
    next: [],
  },
];

const pipeline: PipelineDefinition = {
  pipeline_id: "research.current",
  version: 1,
  name: "Research",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["dense"],
  stages,
};

describe("pipeline relational diagrams", () => {
  it("lays configured stages out with normal and fallback edges", () => {
    const diagram = layoutPipelineDiagram(stages, ["dense"]);

    expect(diagram.nodes.map((node) => node.id)).toEqual(["dense", "lexical", "rerank"]);
    expect(diagram.edges.some((edge) => edge.kind === "next" && edge.from === "dense")).toBe(true);
    expect(diagram.edges.some((edge) => edge.kind === "on_empty" && edge.to === "lexical")).toBe(
      true,
    );
    expect(diagram.nodes.find((node) => node.id === "rerank")!.x).toBeGreaterThan(
      diagram.nodes.find((node) => node.id === "dense")!.x,
    );
  });

  it("relates an execution trace to the saved configuration", () => {
    const trace: PipelineRunTrace = {
      run_id: "run-1",
      feature: "research",
      pipeline_id: "research.current",
      pipeline_version: 1,
      resolved_pipeline: {},
      resolved_hash: "a".repeat(64),
      status: "completed",
      started_at: "2026-09-29T00:00:00Z",
      stages: [
        {
          stage_id: "dense",
          strategy_id: "retrieve.chroma_similarity",
          strategy_version: 1,
          status: "completed",
          elapsed_ms: 12,
          input_count: 1,
          output_count: 4,
          parameters: {},
          fallback_reason: "empty",
        },
        {
          stage_id: "lexical",
          strategy_id: "retrieve.lexical_bm25",
          strategy_version: 1,
          status: "completed",
          elapsed_ms: 8,
          parameters: {},
        },
      ],
    };

    const configuration = configurationForTrace(trace, [pipeline]);
    const diagram = layoutPipelineDiagram(configuration.stages, configuration.entryStageIds, trace);

    expect(configuration.catalogKey).toBe("research.current@1");
    expect(diagram.nodes.find((node) => node.id === "dense")?.executionStatus).toBe("completed");
    expect(diagram.nodes.find((node) => node.id === "rerank")?.presence).toBe("not_reached");
    expect(
      diagram.edges.find((edge) => edge.kind === "on_empty" && edge.to === "lexical")?.traversed,
    ).toBe(true);
    expect(
      diagram.edges.find((edge) => edge.from === "dense" && edge.kind === "next")?.traversed,
    ).toBe(false);
  });
});

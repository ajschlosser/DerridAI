/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";

import { contractStrategy } from "../../src/components/pipelines/fixtures/pipelineCatalogContract";
import {
  choiceFromKey,
  insertStage,
  reaches,
  bindInput,
  releaseOrderingEdges,
  removeBindingReferences,
  renameBindingReferences,
  setInputBinding,
  strategyFit,
  typesCompatible,
  unsatisfiedInputs,
} from "../../src/domain/pipelineBindings";
import type { PipelineDefinition, PipelineStage } from "../../src/types/pipelines";

const stage = (id: string, strategy: string, next: string[] = []): PipelineStage => ({
  id,
  strategy,
  enabled: true,
  config: {},
  next,
});

function pipeline(): PipelineDefinition {
  return {
    pipeline_id: "p",
    version: 1,
    name: "P",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["query"],
    stages: [
      stage("query", "query.passthrough", ["dense"]),
      stage("dense", "retrieve.chroma_similarity", ["rerank"]),
      stage("rerank", "rerank.cross_encoder", ["pack"]),
      stage("pack", "pack.evidence_context"),
    ],
  };
}

describe("pipeline input bindings", () => {
  it("binds an input to an upstream stage output without touching the graph", () => {
    const next = setInputBinding(pipeline(), "rerank", "query", {
      kind: "stage",
      stage: "query",
      output: "query",
    });
    expect(next?.stages[2].inputs).toEqual({
      query: [{ source: "stage", stage: "query", output: "query" }],
    });
    expect(next?.stages[0].next).toEqual(["dense"]);
  });

  it("adds the edge that makes a chosen producer run first", () => {
    const base = pipeline();
    base.stages.push(stage("side", "query.passthrough"));
    base.entry_stage_ids = ["query", "side"];
    const next = setInputBinding(base, "rerank", "query", {
      kind: "stage",
      stage: "side",
      output: "query",
    });
    expect(next?.stages.find((item) => item.id === "side")?.next).toEqual(["rerank"]);
  });

  it("refuses a binding to a downstream stage, which could only form a cycle", () => {
    expect(
      setInputBinding(pipeline(), "dense", "query", {
        kind: "stage",
        stage: "pack",
        output: "context",
      }),
    ).toBeNull();
    expect(
      setInputBinding(pipeline(), "dense", "query", {
        kind: "stage",
        stage: "dense",
        output: "candidates",
      }),
    ).toBeNull();
  });

  it("returns a port to automatic wiring and drops the empty inputs map", () => {
    const bound = setInputBinding(pipeline(), "rerank", "query", {
      kind: "run_input",
      name: "query",
    });
    expect(bound?.stages[2].inputs).toEqual({ query: [{ source: "run_input", name: "query" }] });
    const reset = setInputBinding(bound as PipelineDefinition, "rerank", "query", null);
    expect("inputs" in (reset?.stages[2] ?? {})).toBe(false);
  });

  it("does not mutate the pipeline it was given", () => {
    const base = pipeline();
    const before = JSON.stringify(base);
    setInputBinding(base, "rerank", "query", { kind: "run_input", name: "query" });
    expect(JSON.stringify(base)).toBe(before);
  });

  it("follows a rename and drops bindings to a removed stage", () => {
    const bound = setInputBinding(pipeline(), "rerank", "query", {
      kind: "stage",
      stage: "query",
      output: "query",
    }) as PipelineDefinition;
    renameBindingReferences(bound, "query", "ask");
    expect(bound.stages[2].inputs?.query[0]).toMatchObject({ stage: "ask" });
    removeBindingReferences(bound, "ask");
    expect("inputs" in bound.stages[2]).toBe(false);
  });

  it("finds reachability through normal and fallback edges", () => {
    const base = pipeline();
    base.stages[1].on_error = "side";
    base.stages.push(stage("side", "rerank.lexical_fallback"));
    expect(reaches(base, "query", "side")).toBe(true);
    expect(reaches(base, "pack", "query")).toBe(false);
  });

  it("maps a chosen option key back to its choice", () => {
    const options = [
      {
        kind: "stage" as const,
        stage: "query",
        output: "query",
        data_type: "query" as const,
        upstream: true,
        possible: true,
      },
      {
        kind: "run_input" as const,
        name: "query",
        data_type: "query" as const,
        upstream: true,
        possible: true,
      },
    ];
    expect(choiceFromKey("run:query", options)?.choice).toEqual({
      kind: "run_input",
      name: "query",
    });
    expect(choiceFromKey("stage:query:query", options)?.choice).toMatchObject({ stage: "query" });
    expect(choiceFromKey("stage:none:none", options)).toBeNull();
  });
});

describe("stage fit and insertion", () => {
  const runInputs = [{ name: "query", data_type: "query" as const }];

  it("accepts a strategy whose first input takes what the producer gives", () => {
    const dense = contractStrategy("retrieve.chroma_similarity");
    const rerank = contractStrategy("rerank.cross_encoder");
    expect(strategyFit(rerank, dense, runInputs).fits).toBe(true);
    const wrong = strategyFit(contractStrategy("llm.generate_answer"), dense, runInputs);
    expect(wrong).toMatchObject({ fits: false, reason: "primary_type", needs: "context_packet" });
  });

  it("starts a path only with a strategy the workflow's own inputs can feed", () => {
    expect(strategyFit(contractStrategy("retrieve.lexical_bm25"), null, runInputs).fits).toBe(true);
    expect(strategyFit(contractStrategy("rerank.cross_encoder"), null, runInputs).fits).toBe(false);
  });

  it("requires the workflow to supply every other required input", () => {
    const dense = contractStrategy("retrieve.chroma_similarity");
    const rerank = contractStrategy("rerank.cross_encoder");
    const corpusOnly = [{ name: "context", data_type: "context_packet" as const }];
    expect(strategyFit(rerank, dense, corpusOnly)).toMatchObject({
      fits: false,
      reason: "missing_input",
      needs: "query",
    });
  });

  it("treats any as compatible with every type", () => {
    expect(typesCompatible("any", "query")).toBe(true);
    expect(typesCompatible("query", "candidate_set")).toBe(false);
  });

  it("inserts with unique ids in the three modes", () => {
    const base = pipeline();
    const branch = insertStage(base, "query.passthrough", "query", "after");
    expect(branch.stageId).toBe("passthrough");
    expect(branch.pipeline.stages[0].next).toEqual(["dense", "passthrough"]);

    const spliced = insertStage(base, "filter.metadata_scope", "dense", "between");
    expect(spliced.pipeline.stages[1].next).toEqual(["metadata_scope"]);
    expect(spliced.pipeline.stages[4].next).toEqual(["rerank"]);

    // A second stage from the same strategy gets a numbered id.
    const twice = insertStage(branch.pipeline, "query.passthrough", "query", "after");
    expect(twice.stageId).toBe("passthrough_2");

    const entry = insertStage(base, "retrieve.lexical_bm25", null, "entry");
    expect(entry.pipeline.entry_stage_ids).toEqual(["query", "lexical_bm25"]);
    expect(base.stages).toHaveLength(4);
  });

  it("counts inputs the server could not wire", () => {
    expect(
      unsatisfiedInputs([{ status: "bound" }, { status: "unbound" }, { status: "mismatch" }]),
    ).toBe(2);
    expect(unsatisfiedInputs(undefined)).toBe(0);
  });

  it("removes an edge it added purely for ordering once the binding is reset", () => {
    const base = pipeline();
    base.stages.push(stage("side", "query.passthrough"));
    base.entry_stage_ids = ["query", "side"];
    const bound = bindInput(base, "rerank", "query", {
      kind: "stage",
      stage: "side",
      output: "query",
    });
    expect(bound?.added).toEqual({ from: "side", to: "rerank" });
    const reset = bindInput(bound!.pipeline, "rerank", "query", null)!;
    const released = releaseOrderingEdges(reset.pipeline, [bound!.added!], "rerank");
    expect(released.pipeline.stages.find((item) => item.id === "side")?.next).toEqual([]);
    expect(released.tracked).toEqual([]);
  });

  it("keeps an ordering edge while another binding on the stage still names the producer", () => {
    const base = pipeline();
    base.stages.push(stage("side", "query.passthrough"));
    base.entry_stage_ids = ["query", "side"];
    const bound = bindInput(base, "rerank", "query", {
      kind: "stage",
      stage: "side",
      output: "query",
    })!;
    const released = releaseOrderingEdges(bound.pipeline, [bound.added!], "rerank");
    expect(released.pipeline.stages.find((item) => item.id === "side")?.next).toEqual(["rerank"]);
  });
});

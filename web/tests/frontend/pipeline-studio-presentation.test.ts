/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";

import {
  defaultPipelineKey,
  groupPipelineVersions,
  pipelineOperationalAttention,
  pipelineComparisonRows,
  pipelineRunTone,
  pipelineStatusTone,
  preferredVersionForGroup,
} from "../../src/domain/pipelineStudioPresentation";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelinePurpose,
} from "../../src/types/pipelines";

function pipeline(id: string, version: number, extra: Partial<PipelineDefinition> = {}) {
  return {
    pipeline_id: id,
    version,
    name: `${id} name`,
    purpose: "research",
    status: "active",
    entry_stage_ids: [],
    stages: [],
    runtime_support: { supported: true },
    ...extra,
  } as PipelineDefinition;
}
const assignment = (id: string, version: number): PipelineAssignment => ({
  feature: "research",
  pipeline_id: id,
  pipeline_version: version,
  scope: "system",
  override_allowed: true,
  source: "system",
});
const purposes = [{ purpose_id: "research", category: "research" }] as PipelinePurpose[];

describe("pipeline version grouping", () => {
  const all = [
    pipeline("a", 1),
    pipeline("a", 3, { status: "draft" }),
    pipeline("a", 2),
    pipeline("b", 1, { status: "draft" }),
  ];

  it("groups by pipeline id, newest version first", () => {
    const groups = groupPipelineVersions(all, [assignment("a", 1)], purposes);
    expect(groups.map((g) => g.pipelineId)).toEqual(["a", "b"]);
    expect(groups[0].versions.map((v) => v.version)).toEqual([3, 2, 1]);
    expect(groups[0].latestVersion.version).toBe(3);
    expect(groups[0].assignedVersion?.version).toBe(1);
    expect(groups[0].category).toBe("research");
  });

  it("prefers assigned, then highest active executable, then latest", () => {
    const versions = all.filter((p) => p.pipeline_id === "a");
    expect(preferredVersionForGroup(versions, [assignment("a", 1)])?.version).toBe(1);
    expect(preferredVersionForGroup(versions, [])?.version).toBe(2);
    const onlyDrafts = all.filter((p) => p.pipeline_id === "b");
    expect(preferredVersionForGroup(onlyDrafts, [])?.version).toBe(1);
    const inspectOnly = [pipeline("c", 1, { runtime_support: { supported: false } })];
    expect(preferredVersionForGroup(inspectOnly, [])?.version).toBe(1);
  });
});

describe("default pipeline selection", () => {
  it("prefers the assigned Research pipeline, then a usable one, then the first", () => {
    const base = {
      purposes,
      vocabulary: {},
      strategies: [],
    } as unknown as PipelineCatalog;
    const list = [
      pipeline("draft", 1, { status: "draft" }),
      pipeline("usable", 1),
      pipeline("assigned", 4),
    ];
    expect(
      defaultPipelineKey({ ...base, pipelines: list, assignments: [assignment("assigned", 4)] }),
    ).toBe("assigned@4");
    expect(defaultPipelineKey({ ...base, pipelines: list, assignments: [] })).toBe("usable@1");
    expect(defaultPipelineKey({ ...base, pipelines: [list[0]], assignments: [] })).toBe("draft@1");
    expect(defaultPipelineKey({ ...base, pipelines: [], assignments: [] })).toBe("");
  });
});

describe("status tones", () => {
  it("centralises definition and execution tones", () => {
    expect(pipelineStatusTone("active")).toBe("success");
    expect(pipelineStatusTone("draft")).toBe("neutral");
    expect(pipelineStatusTone("disabled")).toBe("warning");
    expect(pipelineRunTone("timed_out")).toBe("danger");
    expect(pipelineRunTone("running")).toBe("info");
    expect(pipelineRunTone("skipped")).toBe("neutral");
  });
});

describe("operational attention", () => {
  const workflow = (category: string, failed: number, fallback: number) => ({
    category,
    features: [],
    run_count: 10,
    failed_count: failed,
    fallback_run_count: fallback,
    warning_run_count: 0,
    p95_elapsed_ms: 100,
  });
  const strategy = (id: string, failed: number, issues: number, fallbacks: number) => ({
    strategy_id: id,
    stage_ids: [],
    executions: 5,
    fallback_count: fallbacks,
    warning_count: 0,
    model_call_count: 0,
    issue_count: issues,
    status_counts: (failed ? { failed } : {}) as Record<string, number>,
  });

  it("drops healthy rows and orders by failures, then issues, then fallbacks", () => {
    const rows = pipelineOperationalAttention({
      workflows: [workflow("research", 1, 9), workflow("evidence", 0, 0), workflow("search", 3, 0)],
      strategies: [
        strategy("rerank.cross_encoder", 0, 4, 1),
        strategy("retrieve.dense", 0, 4, 6),
        strategy("quiet", 0, 0, 0),
      ],
    });
    expect(rows.map((row) => `${row.kind}:${row.id}`)).toEqual([
      "workflow:search",
      "workflow:research",
      "strategy:retrieve.dense",
      "strategy:rerank.cross_encoder",
    ]);
  });
});

describe("aligned comparison rows", () => {
  const evidence = (id: string, rank: number) => ({
    record_id: id,
    rank,
    work: "",
    citation: "",
    retrieval_hits: [],
  });
  it("lists shared records in A's order, then A-only, then B-only", () => {
    const rows = pipelineComparisonRows({
      left: { evidence: [evidence("a", 1), evidence("b", 2), evidence("c", 3)] },
      right: { evidence: [evidence("d", 1), evidence("c", 2), evidence("a", 3)] },
    } as never);
    expect(rows.map((row) => [row.recordId, row.presence])).toEqual([
      ["a", "both"],
      ["c", "both"],
      ["b", "left"],
      ["d", "right"],
    ]);
    expect(rows[0].right?.rank).toBe(3);
    expect(rows[2].right).toBeNull();
  });
});

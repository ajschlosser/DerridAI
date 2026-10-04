/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026 Aaron John Schlosser, PhD
 */

import { describe, expect, it } from "vitest";
import {
  effectiveOverrideValue,
  overridesForPipeline,
  setStageOverride,
  withOverridesForPipeline,
} from "../../src/domain/pipelineOverrides";
import type { PipelineConfigOverrideSet, PipelineDefinition } from "../../src/types/pipelines";

const pipeline = {
  pipeline_id: "research.current",
  version: 3,
  name: "Research current",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["rerank"],
  stages: [
    {
      id: "rerank",
      strategy: "rerank.cross_encoder",
      enabled: true,
      config: { top_k: 24 },
      next: [],
    },
  ],
} as PipelineDefinition;

describe("pipeline configuration override layers", () => {
  it("resolves Pipeline Studio, Settings, then run precedence", () => {
    const settings = setStageOverride(pipeline, null, "rerank", "top_k", 32);
    const run = setStageOverride(pipeline, null, "rerank", "top_k", 48);
    const stage = pipeline.stages[0];
    const rule = { type: "integer", minimum: 1, maximum: 500, default: 24 };

    expect(
      effectiveOverrideValue({
        stage,
        key: "top_k",
        rule,
        settingsOverrides: settings,
        runOverrides: run,
      }),
    ).toEqual({
      pipeline: 24,
      settings: 32,
      run: 48,
      effective: undefined,
      value: 48,
      source: "run",
    });
  });

  it("keeps saved Settings overrides bound to an exact immutable pipeline version", () => {
    const settings = setStageOverride(pipeline, null, "rerank", "top_k", 32);
    const saved = withOverridesForPipeline({}, pipeline, settings);
    expect(overridesForPipeline(saved, pipeline)?.stages.rerank.top_k).toBe(32);

    const nextVersion = { ...pipeline, version: 4 };
    expect(overridesForPipeline(saved, nextVersion)).toBeNull();
  });

  it("removes an empty override set instead of shadowing Pipeline Studio", () => {
    const empty: PipelineConfigOverrideSet = {
      pipeline_id: pipeline.pipeline_id,
      pipeline_version: pipeline.version,
      stages: {},
    };
    expect(withOverridesForPipeline({ "research.current@3": empty }, pipeline, null)).toEqual({});
  });
});

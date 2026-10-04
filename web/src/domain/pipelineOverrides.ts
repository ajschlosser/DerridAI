/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import type {
  PipelineConfigOverrideSet,
  PipelineDefinition,
  PipelineStage,
} from "../types/pipelines";

export function pipelineVersionKey(
  pipeline: Pick<PipelineDefinition, "pipeline_id" | "version">,
): string {
  return `${pipeline.pipeline_id}@${pipeline.version}`;
}

export function emptyPipelineConfigOverrides(
  pipeline: Pick<PipelineDefinition, "pipeline_id" | "version">,
): PipelineConfigOverrideSet {
  return {
    pipeline_id: pipeline.pipeline_id,
    pipeline_version: pipeline.version,
    stages: {},
  };
}

export function clonePipelineConfigOverrides(
  value: PipelineConfigOverrideSet | null | undefined,
): PipelineConfigOverrideSet | null {
  if (!value) return null;
  return {
    pipeline_id: String(value.pipeline_id || ""),
    pipeline_version: Number(value.pipeline_version || 0),
    stages: Object.fromEntries(
      Object.entries(value.stages || {}).map(([stageId, config]) => [
        stageId,
        { ...(config || {}) },
      ]),
    ),
  };
}

export function overridesForPipeline(
  saved: Record<string, PipelineConfigOverrideSet> | null | undefined,
  pipeline: PipelineDefinition | null | undefined,
): PipelineConfigOverrideSet | null {
  if (!pipeline) return null;
  const candidate = saved?.[pipelineVersionKey(pipeline)];
  if (
    !candidate ||
    candidate.pipeline_id !== pipeline.pipeline_id ||
    candidate.pipeline_version !== pipeline.version
  ) {
    return null;
  }
  return clonePipelineConfigOverrides(candidate);
}

export function withOverridesForPipeline(
  saved: Record<string, PipelineConfigOverrideSet> | null | undefined,
  pipeline: PipelineDefinition,
  overrideSet: PipelineConfigOverrideSet | null,
): Record<string, PipelineConfigOverrideSet> {
  const next = { ...(saved || {}) };
  const key = pipelineVersionKey(pipeline);
  const clean = clonePipelineConfigOverrides(overrideSet);
  if (!clean || !Object.values(clean.stages).some((config) => Object.keys(config).length)) {
    delete next[key];
  } else {
    next[key] = clean;
  }
  return next;
}

export function stageOverrideValue(
  overrideSet: PipelineConfigOverrideSet | null | undefined,
  stageId: string,
  key: string,
): unknown {
  const config = overrideSet?.stages?.[stageId];
  return config && Object.prototype.hasOwnProperty.call(config, key) ? config[key] : undefined;
}

export function hasStageOverride(
  overrideSet: PipelineConfigOverrideSet | null | undefined,
  stageId: string,
  key: string,
): boolean {
  const config = overrideSet?.stages?.[stageId];
  return Boolean(config && Object.prototype.hasOwnProperty.call(config, key));
}

export function setStageOverride(
  pipeline: Pick<PipelineDefinition, "pipeline_id" | "version">,
  current: PipelineConfigOverrideSet | null | undefined,
  stageId: string,
  key: string,
  value: unknown,
): PipelineConfigOverrideSet {
  const next =
    clonePipelineConfigOverrides(current) || emptyPipelineConfigOverrides(pipeline as PipelineDefinition);
  next.pipeline_id = pipeline.pipeline_id;
  next.pipeline_version = pipeline.version;
  next.stages[stageId] = { ...(next.stages[stageId] || {}), [key]: value };
  return next;
}

export function clearStageOverride(
  pipeline: Pick<PipelineDefinition, "pipeline_id" | "version">,
  current: PipelineConfigOverrideSet | null | undefined,
  stageId: string,
  key: string,
): PipelineConfigOverrideSet {
  const next =
    clonePipelineConfigOverrides(current) || emptyPipelineConfigOverrides(pipeline as PipelineDefinition);
  const stage = { ...(next.stages[stageId] || {}) };
  delete stage[key];
  if (Object.keys(stage).length) next.stages[stageId] = stage;
  else delete next.stages[stageId];
  return next;
}

export function pipelineConfiguredValue(
  stage: PipelineStage,
  key: string,
  _rule: Record<string, unknown>,
) {
  // Only persisted stage configuration belongs to the Pipeline Studio layer.
  // A registry/schema default may be useful when seeding a new override, but
  // presenting it as pipeline-owned would make provenance misleading.
  if (Object.prototype.hasOwnProperty.call(stage.config || {}, key)) return stage.config[key];
  return undefined;
}

export function effectiveOverrideValue({
  stage,
  key,
  rule,
  settingsOverrides,
  runOverrides,
}: {
  stage: PipelineStage;
  key: string;
  rule: Record<string, unknown>;
  settingsOverrides?: PipelineConfigOverrideSet | null;
  runOverrides?: PipelineConfigOverrideSet | null;
}) {
  const pipeline = pipelineConfiguredValue(stage, key, rule);
  const settings = stageOverrideValue(settingsOverrides, stage.id, key);
  const run = stageOverrideValue(runOverrides, stage.id, key);
  if (run !== undefined) return { value: run, source: "run" as const, pipeline, settings, run };
  if (settings !== undefined)
    return { value: settings, source: "settings" as const, pipeline, settings, run };
  return { value: pipeline, source: "pipeline" as const, pipeline, settings, run };
}

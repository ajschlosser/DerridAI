/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

// Presentation helpers over the server's pipeline purpose and strategy
// contracts. The server decides which purposes exist, which feature consumes
// each one, its workflow category, its guarantees and which strategies its
// adapter can run; this module only looks those answers up and localizes them.
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineStage,
  PipelineStrategy,
  PipelineStrategyFit,
  PipelineVocabularyTerm,
  PipelineWorkflowVocabulary,
} from "../types/pipelines";
import type { PipelineTranslator } from "./pipelinePresentation";

export type PipelinePurposeTextField =
  | "label"
  | "description"
  | "consumer"
  | "input"
  | "output"
  | "authority";

const PURPOSE_FIELDS: Record<
  PipelinePurposeTextField,
  { key: keyof PipelinePurpose; fallback: keyof PipelinePurpose }
> = {
  label: { key: "label_key", fallback: "label" },
  description: { key: "description_key", fallback: "description" },
  consumer: { key: "consumer_key", fallback: "consumer" },
  input: { key: "input_key", fallback: "input_semantics" },
  output: { key: "output_key", fallback: "output_semantics" },
  authority: { key: "authority_key", fallback: "authority_semantics" },
};

export function purposeText(
  purpose: PipelinePurpose,
  field: PipelinePurposeTextField,
  t: PipelineTranslator,
): string {
  const spec = PURPOSE_FIELDS[field];
  return t(String(purpose[spec.key]), String(purpose[spec.fallback]));
}

export function termLabel(term: PipelineVocabularyTerm, t: PipelineTranslator) {
  return t(term.label_key, term.label);
}

export function termDescription(term: PipelineVocabularyTerm, t: PipelineTranslator) {
  return t(term.description_key, term.description);
}

export function findTerm(terms: PipelineVocabularyTerm[] | undefined, id: string | undefined) {
  return (terms || []).find((term) => term.id === id) || null;
}

export function purposeById(purposes: PipelinePurpose[], purposeId: string) {
  return purposes.find((purpose) => purpose.purpose_id === purposeId) || null;
}

export function purposeForFeature(purposes: PipelinePurpose[], feature: string) {
  return purposes.find((purpose) => purpose.consuming_feature === feature) || null;
}

/** Label for a raw purpose ID or feature; falls back to the raw value when unregistered. */
export function purposeLabelFor(
  purposes: PipelinePurpose[],
  purposeId: string,
  t: PipelineTranslator,
) {
  const purpose = purposeById(purposes, purposeId);
  return purpose ? purposeText(purpose, "label", t) : purposeId;
}

export type PipelineWorkflowGroup = {
  category: PipelineVocabularyTerm;
  pipelines: PipelineDefinition[];
};

/**
 * Group pipelines under the server's workflow categories, in the server's
 * order. Pipelines whose purpose is unregistered are returned separately so
 * they stay visible rather than silently disappearing.
 */
export function groupPipelinesByWorkflow(
  pipelines: PipelineDefinition[],
  purposes: PipelinePurpose[],
  vocabulary: PipelineWorkflowVocabulary,
) {
  const groups: PipelineWorkflowGroup[] = vocabulary.categories.map((category) => ({
    category,
    pipelines: pipelines.filter(
      (pipeline) => purposeById(purposes, pipeline.purpose)?.category === category.id,
    ),
  }));
  const unclassified = pipelines.filter((pipeline) => !purposeById(purposes, pipeline.purpose));
  return { groups: groups.filter((group) => group.pipelines.length), unclassified };
}

export function pipelineCategory(pipeline: PipelineDefinition, purposes: PipelinePurpose[]) {
  return purposeById(purposes, pipeline.purpose)?.category || "";
}

export type StrategyUsage = {
  pipelines: PipelineDefinition[];
  categories: string[];
};

/** Which saved or built-in pipelines use a strategy in an enabled stage, and under which workflows. */
export function strategyUsage(
  strategyId: string,
  pipelines: PipelineDefinition[],
  purposes: PipelinePurpose[],
  vocabulary: PipelineWorkflowVocabulary,
): StrategyUsage {
  const using = pipelines.filter((pipeline) =>
    pipeline.stages.some((stage) => stage.enabled && stage.strategy === strategyId),
  );
  const present = new Set<string>(using.map((pipeline) => pipelineCategory(pipeline, purposes)));
  return {
    pipelines: using,
    categories: vocabulary.categories.map((term) => term.id).filter((id) => present.has(id)),
  };
}

export type StrategyComputation = "deterministic" | "learned" | "generative";

export function strategyComputation(strategy: PipelineStrategy): StrategyComputation {
  if (strategy.invokes_llm) return "generative";
  return strategy.deterministic ? "deterministic" : "learned";
}

export type StrategyPickerGroups = Record<PipelineStrategyFit, PipelineStrategy[]>;

/** Split registered strategies by how the purpose's runtime adapter treats them. */
export function strategyPickerGroups(
  strategies: PipelineStrategy[],
  purpose: PipelinePurpose | null,
): StrategyPickerGroups {
  const groups: StrategyPickerGroups = { supported: [], inspect_only: [], output_contract: [] };
  for (const strategy of strategies) {
    // Without a registered purpose nothing can be recommended; every strategy
    // stays available as an inspect-only choice.
    const fit = purpose
      ? purpose.strategy_fit[strategy.strategy_id] || "inspect_only"
      : "inspect_only";
    groups[fit].push(strategy);
  }
  return groups;
}

function stageLayers(stages: PipelineStage[], entryStageIds: string[]) {
  const enabled = stages.filter((stage) => stage.enabled);
  const known = new Set(enabled.map((stage) => stage.id));
  const layer = new Map<string, number>();
  for (const id of entryStageIds) if (known.has(id)) layer.set(id, 0);
  for (let pass = 0; pass <= enabled.length; pass += 1) {
    let changed = false;
    for (const stage of enabled) {
      const source = layer.get(stage.id);
      if (source == null) continue;
      const targets = [
        ...stage.next,
        stage.on_empty,
        stage.on_unavailable,
        stage.on_timeout,
        stage.on_error,
      ];
      for (const target of targets) {
        if (!target || !known.has(target)) continue;
        const next = Math.min(source + 1, enabled.length);
        if ((layer.get(target) ?? -1) < next) {
          layer.set(target, next);
          changed = true;
        }
      }
    }
    if (!changed) break;
  }
  return layer;
}

/**
 * The broad phases a pipeline passes through, in graph order, derived from each
 * enabled stage's registered phase. Consecutive stages in one phase collapse,
 * and pipelines skip phases they do not have: this is a reading aid over the
 * executable graph, not a second pipeline model.
 */
export function pipelinePhaseSequence(
  pipeline: Pick<PipelineDefinition, "stages" | "entry_stage_ids">,
  strategies: PipelineStrategy[],
) {
  const byId = new Map(strategies.map((strategy) => [strategy.strategy_id, strategy]));
  const layers = stageLayers(pipeline.stages, pipeline.entry_stage_ids);
  const ordered = [...layers.entries()].sort((left, right) => left[1] - right[1]);
  const stageById = new Map(pipeline.stages.map((stage) => [stage.id, stage]));
  const phases: string[] = [];
  for (const [stageId] of ordered) {
    const phase = byId.get(stageById.get(stageId)?.strategy || "")?.phase;
    if (phase && phases[phases.length - 1] !== phase) phases.push(phase);
  }
  return phases;
}

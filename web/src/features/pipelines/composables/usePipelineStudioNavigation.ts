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

import { ref, watch, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

export type PipelineStudioSection = "pipelines" | "strategies" | "executions" | "operations";
export type PipelineOperationsSection = "health" | "compare" | "benchmarks";

export const PIPELINE_STUDIO_SECTIONS: readonly PipelineStudioSection[] = [
  "pipelines",
  "strategies",
  "executions",
  "operations",
];
export const PIPELINE_OPERATIONS_SECTIONS: readonly PipelineOperationsSection[] = [
  "health",
  "compare",
  "benchmarks",
];

export interface PipelineDefinitionFilters {
  query: string;
  status: string;
}

export interface PipelineStrategyFilters {
  query: string;
  family: string;
  computation: string;
  capability: string;
  effect: string;
  workflow: string;
}

export interface PipelineRunFilters {
  query: string;
  /** Workflow category; the server expands it to the features that consume it. */
  category: string;
  feature: string;
  pipelineId: string;
  status: string;
  owner: string;
}

export interface PipelineStudioNavigation {
  section: Ref<PipelineStudioSection>;
  selectedPipelineKey: Ref<string>;
  pipelineWorkflow: Ref<string>;
  selectedStrategyId: Ref<string>;
  selectedRunId: Ref<string>;
  operationsSection: Ref<PipelineOperationsSection>;
  pipelineFilters: Ref<PipelineDefinitionFilters>;
  strategyFilters: Ref<PipelineStrategyFilters>;
  runFilters: Ref<PipelineRunFilters>;
  runOffset: Ref<number>;

  selectSection(section: PipelineStudioSection): void;
  selectPipeline(key: string): void;
  selectWorkflow(category: string): void;
  selectStrategy(id: string): void;
  selectRun(id: string): void;
  selectOperationsSection(section: PipelineOperationsSection): void;
  setPipelineFilters(filters: PipelineDefinitionFilters): void;
  setStrategyFilters(filters: PipelineStrategyFilters): void;
  /**
   * Persist the current selections and filters to the URL. Deliberate navigation (a new section,
   * pipeline, strategy, run or Operations tab) pushes a history entry so Back restores it; typing
   * a filter and load-time normalization replace the current entry.
   */
  syncRouteState(mode?: "push" | "replace"): void;
}

export function emptyRunFilters(): PipelineRunFilters {
  return { query: "", category: "", feature: "", pipelineId: "", status: "", owner: "" };
}

function oneOf<T extends string>(values: readonly T[], value: unknown, fallback: T): T {
  return values.includes(value as T) ? (value as T) : fallback;
}

const text = (value: unknown) =>
  Array.isArray(value) ? String(value[0] ?? "") : String(value ?? "");

/**
 * Route-addressable Pipeline Studio state. The URL is the source of truth for which section,
 * pipeline version, strategy, execution and filters are showing, so Back/Forward restores context.
 * `onRunQueryChange` fires when a route change alters the server-side execution query.
 */
export function usePipelineStudioNavigation(
  onRunQueryChange?: () => void,
): PipelineStudioNavigation {
  const route = useRoute();
  const router = useRouter();

  const section = ref<PipelineStudioSection>("pipelines");
  const operationsSection = ref<PipelineOperationsSection>("health");
  const selectedPipelineKey = ref("");
  const pipelineWorkflow = ref("");
  const selectedStrategyId = ref("");
  const selectedRunId = ref("");
  const pipelineFilters = ref<PipelineDefinitionFilters>({ query: "", status: "" });
  const strategyFilters = ref<PipelineStrategyFilters>({
    query: "",
    family: "",
    computation: "",
    capability: "",
    effect: "",
    workflow: "",
  });
  const runFilters = ref<PipelineRunFilters>(emptyRunFilters());
  const runOffset = ref(0);

  function readRoute() {
    const q = route.query;
    section.value = oneOf(PIPELINE_STUDIO_SECTIONS, text(q.section), "pipelines");
    operationsSection.value = oneOf(PIPELINE_OPERATIONS_SECTIONS, text(q.operation), "health");
    selectedPipelineKey.value = text(q.pipeline);
    pipelineWorkflow.value = text(q.workflow);
    selectedStrategyId.value = text(q.strategy);
    selectedRunId.value = text(q.run);
    pipelineFilters.value = { query: text(q.pipeline_q), status: text(q.pipeline_status) };
    strategyFilters.value = {
      query: text(q.strategy_q),
      family: text(q.strategy_family),
      computation: text(q.strategy_computation),
      capability: text(q.strategy_capability),
      effect: text(q.strategy_effect),
      workflow: text(q.strategy_workflow),
    };
    runFilters.value = {
      query: text(q.q),
      category: text(q.run_workflow),
      feature: text(q.feature),
      pipelineId: text(q.pipeline_id),
      status: text(q.status),
      owner: text(q.owner),
    };
    runOffset.value = Math.max(0, Number(text(q.offset) || 0) || 0);
  }

  function syncRouteState(mode: "push" | "replace" = "replace") {
    const query: Record<string, string | string[] | undefined> = {
      ...route.query,
      section: section.value === "pipelines" ? undefined : section.value,
      operation:
        section.value === "operations" && operationsSection.value !== "health"
          ? operationsSection.value
          : undefined,
      pipeline: selectedPipelineKey.value || undefined,
      workflow: pipelineWorkflow.value || undefined,
      pipeline_q: pipelineFilters.value.query || undefined,
      pipeline_status: pipelineFilters.value.status || undefined,
      strategy: selectedStrategyId.value || undefined,
      strategy_q: strategyFilters.value.query || undefined,
      strategy_family: strategyFilters.value.family || undefined,
      strategy_computation: strategyFilters.value.computation || undefined,
      strategy_capability: strategyFilters.value.capability || undefined,
      strategy_effect: strategyFilters.value.effect || undefined,
      strategy_workflow: strategyFilters.value.workflow || undefined,
      run: selectedRunId.value || undefined,
      q: runFilters.value.query || undefined,
      run_workflow: runFilters.value.category || undefined,
      feature: runFilters.value.feature || undefined,
      pipeline_id: runFilters.value.pipelineId || undefined,
      status: runFilters.value.status || undefined,
      owner: runFilters.value.owner || undefined,
      offset: runOffset.value ? String(runOffset.value) : undefined,
    };
    for (const key of Object.keys(query)) {
      if (query[key] === undefined || query[key] === "") delete query[key];
    }
    const current = route.query;
    const same =
      Object.keys(query).length === Object.keys(current).length &&
      Object.entries(query).every(
        ([key, value]) => String(current[key] || "") === String(value || ""),
      );
    if (!same) void router[mode]({ name: "pipelines", query });
  }

  function selectSection(next: PipelineStudioSection) {
    section.value = next;
    syncRouteState("push");
  }
  function selectPipeline(key: string) {
    selectedPipelineKey.value = key;
    section.value = "pipelines";
    syncRouteState("push");
  }
  function selectWorkflow(category: string) {
    pipelineWorkflow.value = category;
    syncRouteState();
  }
  function selectStrategy(id: string) {
    selectedStrategyId.value = id;
    syncRouteState("push");
  }
  function selectRun(id: string) {
    selectedRunId.value = id;
    syncRouteState("push");
  }
  function selectOperationsSection(next: PipelineOperationsSection) {
    operationsSection.value = next;
    syncRouteState("push");
  }
  function setPipelineFilters(filters: PipelineDefinitionFilters) {
    pipelineFilters.value = filters;
    syncRouteState();
  }
  function setStrategyFilters(filters: PipelineStrategyFilters) {
    strategyFilters.value = filters;
    syncRouteState();
  }

  readRoute();
  watch(
    () => route.query,
    () => {
      const signature = () =>
        JSON.stringify({ filters: runFilters.value, offset: runOffset.value });
      const previous = signature();
      readRoute();
      if (previous !== signature()) onRunQueryChange?.();
    },
  );

  return {
    section,
    selectedPipelineKey,
    pipelineWorkflow,
    selectedStrategyId,
    selectedRunId,
    operationsSection,
    pipelineFilters,
    strategyFilters,
    runFilters,
    runOffset,
    selectSection,
    selectPipeline,
    selectWorkflow,
    selectStrategy,
    selectRun,
    selectOperationsSection,
    setPipelineFilters,
    setStrategyFilters,
    syncRouteState,
  };
}

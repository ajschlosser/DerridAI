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

import { computed, ref, watch, type Ref } from "vue";
import { pipelinesApi } from "../../../api/pipelines";
import { useDataQuery } from "../../../realtime/dataQuery";
import type { PipelineRunFilters } from "./usePipelineStudioNavigation";
import type { PipelineRunTrace } from "../../../types/pipelines";

export const PIPELINE_RUN_PAGE_SIZE = 25;
const METRICS_SAMPLE = 250;

/**
 * Server state for Pipeline Studio: the catalog (`pipelines`), plus the execution page, its
 * focused trace and the health metrics (`pipeline_runs`). Realtime invalidation refetches them;
 * the Studio has no refresh button. Selection and filters stay with the navigation composable.
 */
export function usePipelineStudioData(nav: {
  runFilters: Ref<PipelineRunFilters>;
  runOffset: Ref<number>;
  selectedRunId: Ref<string>;
}) {
  const catalogQuery = useDataQuery("pipelines", () => pipelinesApi.catalog());
  const metricsQuery = useDataQuery(
    "pipeline_runs",
    () => pipelinesApi.metrics({ limit: METRICS_SAMPLE }),
    { detail: ["metrics"] },
  );
  const runsQuery = useDataQuery(
    "pipeline_runs",
    () => {
      const filters = nav.runFilters.value;
      return pipelinesApi.runs({
        category: filters.category || undefined,
        feature: filters.feature || undefined,
        owner: filters.owner || undefined,
        pipelineId: filters.pipelineId || undefined,
        status: filters.status || undefined,
        query: filters.query || undefined,
        limit: PIPELINE_RUN_PAGE_SIZE,
        offset: nav.runOffset.value,
      });
    },
    { detail: () => ["runs", nav.runFilters.value, nav.runOffset.value] },
  );

  // Keep the last good page while a new key loads so the table never blanks during a refetch.
  const runs = ref<PipelineRunTrace[]>([]);
  const runTotal = ref(0);
  watch(
    () => runsQuery.data.value,
    (page) => {
      if (!page) return;
      runs.value = page.runs || [];
      runTotal.value = page.total ?? runs.value.length;
    },
    { immediate: true },
  );

  // A selected trace that is not on the current page is fetched on its own.
  const offPage = computed(
    () =>
      Boolean(nav.selectedRunId.value) &&
      !runs.value.some((r) => r.run_id === nav.selectedRunId.value),
  );
  const focusQuery = useDataQuery(
    "pipeline_runs",
    async () => (await pipelinesApi.run(nav.selectedRunId.value)).run,
    { detail: () => ["run", nav.selectedRunId.value], enabled: offPage },
  );

  const focusedRun = computed<PipelineRunTrace | null>(
    () =>
      runs.value.find((r) => r.run_id === nav.selectedRunId.value) ||
      (offPage.value ? focusQuery.data.value || null : null),
  );

  watch(
    [runs, () => focusQuery.isError.value, () => nav.selectedRunId.value],
    () => {
      if (!runsQuery.data.value) return;
      if (!nav.selectedRunId.value && runs.value.length)
        nav.selectedRunId.value = runs.value[0].run_id;
      else if (offPage.value && focusQuery.isError.value)
        nav.selectedRunId.value = runs.value[0]?.run_id || "";
    },
    { immediate: true },
  );

  const error = computed(() => {
    const failure = catalogQuery.error.value || metricsQuery.error.value || runsQuery.error.value;
    return failure ? (failure instanceof Error ? failure.message : String(failure)) : "";
  });

  /** Read everything again now (after a local mutation); realtime covers other writers. */
  async function reload() {
    await Promise.all([catalogQuery.refetch(), metricsQuery.refetch(), runsQuery.refetch()]);
  }

  return {
    catalog: computed(() => catalogQuery.data.value ?? null),
    metrics: computed(() => metricsQuery.data.value ?? null),
    runs,
    runTotal,
    focusedRun,
    loading: computed(() => catalogQuery.isPending.value),
    error,
    reload,
  };
}

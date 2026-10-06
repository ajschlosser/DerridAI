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

  // Bind retained execution rows to the query identity that produced them. Same-key
  // refreshes may keep useful rows visible, but changing filters/page must never relabel
  // the previous result set as though it belonged to the new request.
  const requestedRunsIdentity = computed(() =>
    JSON.stringify([nav.runFilters.value, nav.runOffset.value]),
  );
  const shownRunsIdentity = ref("");
  const retainedRuns = ref<PipelineRunTrace[]>([]);
  const retainedRunTotal = ref(0);
  watch(
    () => runsQuery.data.value,
    (page) => {
      if (!page) return;
      retainedRuns.value = page.runs || [];
      retainedRunTotal.value = page.total ?? retainedRuns.value.length;
      shownRunsIdentity.value = requestedRunsIdentity.value;
    },
    { immediate: true },
  );
  const runsAreCurrent = computed(
    () => shownRunsIdentity.value === requestedRunsIdentity.value,
  );
  const runs = computed(() => (runsAreCurrent.value ? retainedRuns.value : []));
  const runTotal = computed(() => (runsAreCurrent.value ? retainedRunTotal.value : 0));

  // A selected trace that is not on the current page is fetched on its own. Do not use
  // retained rows from another filter/page identity to satisfy that selection.
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
      if (!runsAreCurrent.value || !runsQuery.data.value) return;
      if (!nav.selectedRunId.value && runs.value.length)
        nav.selectedRunId.value = runs.value[0].run_id;
      else if (offPage.value && focusQuery.isError.value)
        nav.selectedRunId.value = runs.value[0]?.run_id || "";
    },
    { immediate: true },
  );

  const messageFor = (failure: unknown) =>
    failure ? (failure instanceof Error ? failure.message : String(failure)) : "";

  /** Read everything again now (after a local mutation); realtime covers other writers. */
  async function reload() {
    await Promise.all([catalogQuery.refetch(), metricsQuery.refetch(), runsQuery.refetch()]);
  }

  return {
    catalog: computed(() => catalogQuery.data.value ?? null),
    catalogPending: computed(() => catalogQuery.isPending.value),
    catalogRefreshing: computed(
      () => catalogQuery.isFetching.value && Boolean(catalogQuery.data.value),
    ),
    catalogError: computed(() => messageFor(catalogQuery.error.value)),
    metrics: computed(() => metricsQuery.data.value ?? null),
    metricsPending: computed(
      () => metricsQuery.isFetching.value && !metricsQuery.data.value,
    ),
    metricsRefreshing: computed(
      () => metricsQuery.isFetching.value && Boolean(metricsQuery.data.value),
    ),
    metricsError: computed(() => messageFor(metricsQuery.error.value)),
    runs,
    runTotal,
    focusedRun,
    runsPending: computed(() => runsQuery.isFetching.value && !runsAreCurrent.value),
    runsRefreshing: computed(() => runsQuery.isFetching.value && runsAreCurrent.value),
    runsError: computed(() => messageFor(runsQuery.error.value)),
    reloadRuns: () => runsQuery.refetch(),
    reloadMetrics: () => metricsQuery.refetch(),
    reload,
  };
}

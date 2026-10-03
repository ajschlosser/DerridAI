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

import { onBeforeUnmount, ref, watch, type Ref } from "vue";
import { ApiError } from "../api/http";
import { pipelinesApi } from "../api/pipelines";
import { useI18nStore } from "../stores/i18n";
import type { PipelineAnalysis, PipelineDefinition } from "../types/pipelines";

/**
 * Keeps a server analysis (input wiring, declared cost, expected latency) in step with a
 * pipeline draft that changes as the administrator edits it. Calls follow `delayMs` of quiet,
 * an older request is aborted when a newer one starts, and the last good analysis stays
 * visible while the next one loads so the panel does not flicker between edits.
 */
export function usePipelineAnalysis(pipeline: Ref<PipelineDefinition | null>, delayMs = 400) {
  const analysis = ref<PipelineAnalysis | null>(null);
  const loading = ref(false);
  const error = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | undefined;
  let generation = 0;

  async function run() {
    const draft = pipeline.value;
    controller?.abort();
    if (!draft) return;
    controller = new AbortController();
    const mine = ++generation;
    loading.value = true;
    try {
      const result = await pipelinesApi.analyze(draft, controller.signal);
      if (mine !== generation) return;
      analysis.value = result;
      error.value = "";
    } catch (cause) {
      if (mine !== generation || (cause instanceof DOMException && cause.name === "AbortError")) {
        return;
      }
      // While a stage id is retyped the draft is briefly invalid; say so rather than echo the raw 422.
      error.value =
        cause instanceof ApiError && cause.status === 422
          ? useI18nStore().t(
              "pipelines.analysis_draft_incomplete",
              "The draft is incomplete, so it cannot be analysed yet. The last complete analysis is shown.",
            )
          : cause instanceof Error
            ? cause.message
            : String(cause);
    } finally {
      if (mine === generation) loading.value = false;
    }
  }

  function schedule(immediate = false) {
    if (timer !== undefined) clearTimeout(timer);
    timer = immediate ? undefined : setTimeout(() => void run(), delayMs);
    if (immediate) void run();
  }

  watch(
    pipeline,
    (next, previous) => {
      if (!next) {
        // No draft any more: drop the analysis so a later draft never shows a stale one.
        if (timer !== undefined) clearTimeout(timer);
        controller?.abort();
        generation += 1;
        analysis.value = null;
        loading.value = false;
        error.value = "";
        return;
      }
      // A draft that has just appeared is analyzed at once; edits to it follow after a pause.
      schedule(!previous || previous.pipeline_id !== next.pipeline_id);
    },
    { deep: true, immediate: false },
  );
  onBeforeUnmount(() => {
    if (timer !== undefined) clearTimeout(timer);
    controller?.abort();
    generation += 1;
  });

  return { analysis, loading, error, refresh: () => schedule(true) };
}

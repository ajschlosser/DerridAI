/* Copyright 2026 Aaron John Schlosser, PhD. */
import { onMounted, ref } from "vue";
import { pipelinesApi } from "../api/pipelines";
import type { PipelineStrategyLatency } from "../types/pipelines";

/**
 * Observed per-strategy latency from recent execution traces. Figures only decorate the
 * stage picker and strategy details, so a failed read leaves them out rather than raising.
 */
export function useStrategyLatency() {
  const latency = ref<Record<string, PipelineStrategyLatency> | null>(null);
  const sampledRuns = ref(0);
  onMounted(() => {
    pipelinesApi
      .strategyLatency()
      .then((result) => {
        latency.value = result.strategies;
        sampledRuns.value = result.sampled_run_count;
      })
      .catch(() => {
        latency.value = null;
      });
  });
  return { latency, sampledRuns };
}

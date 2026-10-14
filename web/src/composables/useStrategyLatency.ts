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

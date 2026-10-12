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
import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { apiRequest, ApiError } from "../../api/http";
import { useAuthStore } from "../../stores/auth";
import type { ResearchJob } from "../../types/research";
import type { ResearchTurn } from "../../types/researchThreads";

/**
 * Loads one completed turn's immutable result for its exact attempt.
 *
 * A completed turn result is immutable for a specific attempt. Keep it out of
 * the broad research_threads invalidation tree so one thread event does not
 * refetch every historical answer mounted in the browser. Answers whose run
 * identity does not match the turn are never shown as that turn's result.
 */
export function useResearchTurnResult(turn: Ref<ResearchTurn>, wanted: Ref<boolean>) {
  const auth = useAuthStore();
  const allowed = computed(() => Boolean(auth.user && auth.can("rag.run")));
  const answer = useQuery({
    queryKey: computed(() => [
      "research-turn-result",
      auth.user?.id,
      auth.user?.role,
      turn.value.thread_id,
      turn.value.turn_id,
      turn.value.attempt,
      turn.value.job_id,
      turn.value.response_record_id,
    ]),
    queryFn: async () => {
      const current = { ...turn.value };
      if (current.job_id) {
        try {
          return await apiRequest<ResearchJob>(`/api/jobs/${encodeURIComponent(current.job_id)}`);
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 404) throw error;
        }
      }
      return apiRequest<ResearchJob>(
        `/api/research/threads/${encodeURIComponent(current.thread_id)}/turns/${encodeURIComponent(current.turn_id)}/result`,
      );
    },
    enabled: computed(
      () =>
        allowed.value &&
        wanted.value &&
        turn.value.status === "completed" &&
        Boolean(turn.value.job_id || turn.value.response_record_id),
    ),
    staleTime: Number.POSITIVE_INFINITY,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const denied = computed(
    () =>
      answer.error.value instanceof ApiError && [401, 403, 404].includes(answer.error.value.status),
  );
  const result = computed(() =>
    allowed.value &&
    !denied.value &&
    answer.data.value?.id === (turn.value.research_run_id || turn.value.job_id)
      ? answer.data.value?.result
      : null,
  );
  return { answer, allowed, denied, result };
}

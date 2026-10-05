<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->
<script setup lang="ts">
import { computed } from "vue";
import { apiRequest, ApiError } from "../../api/http";
import { useDataQuery } from "../../realtime/dataQuery";
import { useAuthStore } from "../../stores/auth";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchJob } from "../../types/research";
import type { ResearchTurn } from "../../types/researchThreads";

const props = defineProps<{ turn: ResearchTurn }>();
const auth = useAuthStore();
const i18n = useI18nStore();
const allowed = computed(() => Boolean(auth.user && auth.can("rag.run")));
const answer = useDataQuery(
  "research_threads",
  () => apiRequest<ResearchJob>(`/api/jobs/${encodeURIComponent(props.turn.job_id || "")}`),
  {
    detail: () => [
      auth.user?.id,
      auth.user?.role,
      allowed.value,
      "answer",
      props.turn.thread_id,
      props.turn.turn_id,
      props.turn.job_id,
      props.turn.attempt,
    ],
    enabled: () => allowed.value && props.turn.status === "completed" && Boolean(props.turn.job_id),
  },
);
const denied = computed(
  () =>
    answer.error.value instanceof ApiError && [401, 403, 404].includes(answer.error.value.status),
);
const result = computed(() =>
  allowed.value && !denied.value && answer.data.value?.id === props.turn.job_id
    ? answer.data.value?.result
    : null,
);
</script>
<template>
  <section
    v-if="allowed && turn.status === 'completed' && turn.job_id"
    :aria-label="i18n.t('research.answer')"
  >
    <p v-if="answer.isFetching.value" role="status">{{ i18n.t("loading.updating") }}</p>
    <div v-if="answer.error.value" role="alert">
      <p>{{ denied ? i18n.t("research.thread_run_unavailable") : String(answer.error.value) }}</p>
      <button class="btn" type="button" @click="answer.refetch()">{{ i18n.t("ui.retry") }}</button>
    </div>
    <template v-if="result?.answer">
      <p class="thread-answer-text">{{ result.answer }}</p>
      <details v-if="result.evidence?.length">
        <summary>{{ i18n.t("research.works_cited") }}</summary>
        <ul>
          <li v-for="(item, index) in result.evidence" :key="item.evidence_id || index">
            {{ item.full_citation || item.inline_citation || item.evidence_id }}
          </li>
        </ul>
      </details>
    </template>
    <p v-else-if="!answer.isFetching.value && !answer.error.value">
      {{ i18n.t("research.thread_run_unavailable") }}
    </p>
  </section>
</template>
<style scoped>
.thread-answer-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>

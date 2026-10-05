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
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useResearchDraft } from "../../features/research/useResearchDraft";
import { apiRequest, ApiError } from "../../api/http";
import { useDataQuery } from "../../realtime/dataQuery";
import { useAuthStore } from "../../stores/auth";
import { useI18nStore } from "../../stores/i18n";
import ResearchResultPresentation from "./ResearchResultPresentation.vue";
import type { ResearchJob, ResearchResultEvidence } from "../../types/research";
import type { ResearchTurn } from "../../types/researchThreads";

const props = defineProps<{ turn: ResearchTurn }>();
const emit = defineEmits<{
  openRecord: [item: ResearchResultEvidence];
  openRelationships: [item: ResearchResultEvidence, mode: "trace" | "model"];
}>();
const activeEvidenceIndex = ref(0);
const auth = useAuthStore();
const i18n = useI18nStore();
const allowed = computed(() => Boolean(auth.user && auth.can("rag.run")));
const stream = useResearchDraft();
const live = computed(
  () =>
    allowed.value &&
    Boolean(props.turn.job_id) &&
    ["queued", "running"].includes(props.turn.status),
);
// A retry starts a new stream. Scope changes drop advisory text synchronously.
watch(
  () => [
    auth.user?.id,
    auth.user?.role,
    allowed.value,
    props.turn.thread_id,
    props.turn.turn_id,
    props.turn.job_id,
    props.turn.attempt,
    live.value,
  ],
  () => {
    stream.clear();
    activeEvidenceIndex.value = 0;
    if (live.value) stream.follow(props.turn.job_id!);
  },
  { immediate: true, flush: "sync" },
);
onBeforeUnmount(stream.clear);
const answer = useDataQuery(
  "research_threads",
  async () => {
    const turn = { ...props.turn };
    if (turn.job_id) {
      try {
        return await apiRequest<ResearchJob>(`/api/jobs/${encodeURIComponent(turn.job_id)}`);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) throw error;
      }
    }
    return apiRequest<ResearchJob>(
      `/api/research/threads/${encodeURIComponent(turn.thread_id)}/turns/${encodeURIComponent(turn.turn_id)}/result`,
    );
  },
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
    enabled: () =>
      allowed.value &&
      props.turn.status === "completed" &&
      Boolean(props.turn.job_id || props.turn.response_record_id),
  },
);
const denied = computed(
  () =>
    answer.error.value instanceof ApiError && [401, 403, 404].includes(answer.error.value.status),
);
const result = computed(() =>
  allowed.value &&
  !denied.value &&
  answer.data.value?.id === (props.turn.research_run_id || props.turn.job_id)
    ? answer.data.value?.result
    : null,
);
function openRecord(index: number) {
  const item = result.value?.evidence?.[index];
  if (item) emit("openRecord", item);
}
function openRelationships(index: number, mode: "trace" | "model") {
  const item = result.value?.evidence?.[index];
  if (item) emit("openRelationships", item, mode);
}
</script>
<template>
  <section
    v-if="
      allowed && (turn.job_id || turn.response_record_id) && (live || turn.status === 'completed')
    "
    :aria-label="`${i18n.t('research.answer')} ${turn.ordinal}: ${turn.user_question}`"
  >
    <template v-if="live">
      <p role="status">{{ i18n.t("research.draft_heading") }}</p>
      <p>{{ i18n.t("research.draft_help") }}</p>
      <p class="thread-answer-text">{{ stream.draft.value?.text }}</p>
    </template>
    <template v-else>
      <p v-if="answer.isFetching.value" role="status">{{ i18n.t("loading.updating") }}</p>
      <div v-if="answer.error.value" role="alert">
        <p>{{ denied ? i18n.t("research.thread_run_unavailable") : String(answer.error.value) }}</p>
        <button class="btn" type="button" @click="answer.refetch()">
          {{ i18n.t("ui.retry") }}
        </button>
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
        <details>
          <summary>{{ i18n.t("research.thread_inspect_result") }}</summary>
          <ResearchResultPresentation
            :instance-id="`thread-answer-${turn.turn_id}`"
            :instance-label="`${turn.ordinal}: ${turn.user_question}`"
            :job="answer.data.value"
            :result="result"
            :active-evidence-index="activeEvidenceIndex"
            :researcher="!auth.isAdmin"
            read-only
            @evidence="activeEvidenceIndex = $event"
            @select-evidence="activeEvidenceIndex = $event"
            @open-record="openRecord"
            @open-relationships="openRelationships"
          />
          <details v-if="result.research_thread">
            <summary>{{ i18n.t("research.thread_context_audit") }}</summary>
            <pre>{{ JSON.stringify(result.research_thread, null, 2) }}</pre>
          </details>
        </details>
      </template>
      <p v-else-if="!answer.isFetching.value && !answer.error.value">
        {{ i18n.t("research.thread_run_unavailable") }}
      </p>
    </template>
  </section>
</template>
<style scoped>
.thread-answer-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>

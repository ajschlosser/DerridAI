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
import { computed, ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { researchThreadsApi } from "../../api/researchThreads";
import { useDataQuery } from "../../realtime/dataQuery";
import ResearchThreadNavigation from "./ResearchThreadNavigation.vue";
import type { ResearchTurn } from "../../types/researchThreads";
import { ApiError } from "../../api/http";

const props = defineProps<{ threadId: string; jobId: string }>();
const emit = defineEmits<{ select: [id: string]; open: [turn: ResearchTurn]; new: [] }>();
const auth = useAuthStore();
const offset = ref(0);
const allowed = computed(() => Boolean(auth.user && auth.can("rag.run")));
const scope = computed(() => [auth.user?.id, auth.user?.role, allowed.value]);
const list = useDataQuery(
  "research_threads",
  () => researchThreadsApi.list({ offset: offset.value }),
  {
    detail: () => [...scope.value, "list", offset.value],
    enabled: allowed,
  },
);
const detail = useDataQuery("research_threads", () => researchThreadsApi.get(props.threadId), {
  detail: () => [...scope.value, "thread", props.threadId],
  enabled: () => allowed.value && Boolean(props.threadId),
});
const error = computed(() => {
  const value = list.error.value || (props.threadId ? detail.error.value : null);
  return value instanceof Error ? value.message : value ? String(value) : "";
});
// Revoked access/deletion must clear cached content; transient failures retain it.
function inaccessible(value: unknown) {
  return value instanceof ApiError && [401, 403, 404].includes(value.status);
}
function retry() {
  void list.refetch();
  if (props.threadId) void detail.refetch();
}
</script>
<template>
  <ResearchThreadNavigation
    v-if="allowed"
    :threads="inaccessible(list.error.value) ? [] : list.data.value?.threads || []"
    :thread="threadId && !inaccessible(detail.error.value) ? detail.data.value : null"
    :selected-thread-id="threadId"
    :selected-job-id="jobId"
    :offset="offset"
    :loading="list.isFetching.value || (Boolean(threadId) && detail.isFetching.value)"
    :error="error"
    @select="emit('select', $event)"
    @open="emit('open', $event)"
    @new="emit('new')"
    @page="offset = $event"
    @retry="retry"
  />
</template>

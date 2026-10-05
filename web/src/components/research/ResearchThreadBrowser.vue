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
import { computed, ref, watch, onBeforeUnmount, nextTick } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useI18nStore } from "../../stores/i18n";
import ResearchThreadManageDialog from "./ResearchThreadManageDialog.vue";
import { useAuthStore } from "../../stores/auth";
import { researchThreadsApi } from "../../api/researchThreads";
import { useDataQuery } from "../../realtime/dataQuery";
import ResearchThreadAnswer from "./ResearchThreadAnswer.vue";
import ResearchThreadNavigation from "./ResearchThreadNavigation.vue";
import type { ResearchTurn } from "../../types/researchThreads";
import { ApiError } from "../../api/http";

const props = defineProps<{ threadId: string; jobId: string }>();
const emit = defineEmits<{
  select: [id: string];
  open: [turn: ResearchTurn];
  new: [];
  removed: [error?: string];
}>();
const auth = useAuthStore();
const offset = ref(0);
const includeArchived = ref(false);
const dialog = ref<"rename" | "delete" | null>(null);
const busy = ref(false);
const mutationError = ref("");
const notice = ref("");
const client = useQueryClient();
const i18n = useI18nStore();
let operation = 0;
let dialogTrigger: HTMLElement | null = null;
function resetMutation() {
  ++operation;
  dialog.value = null;
  busy.value = false;
  mutationError.value = "";
  notice.value = "";
  dialogTrigger = null;
}
onBeforeUnmount(resetMutation);
const allowed = computed(() => Boolean(auth.user && auth.can("rag.run")));
const scope = computed(() => [auth.user?.id, auth.user?.role, allowed.value]);
const list = useDataQuery(
  "research_threads",
  () => researchThreadsApi.list({ offset: offset.value, includeArchived: includeArchived.value }),
  {
    detail: () => [...scope.value, "list", offset.value, includeArchived.value],
    enabled: allowed,
  },
);
const detail = useDataQuery("research_threads", () => researchThreadsApi.get(props.threadId), {
  detail: () => [...scope.value, "thread", props.threadId],
  enabled: () => allowed.value && Boolean(props.threadId),
});
watch(() => [props.threadId, ...scope.value], resetMutation);
watch(includeArchived, () => {
  offset.value = 0;
});
const error = computed(() => {
  const value = list.error.value || (props.threadId ? detail.error.value : null);
  return value instanceof Error ? value.message : value ? String(value) : "";
});
// Revoked access/deletion must clear cached content; transient failures retain it.
function inaccessible(value: unknown) {
  return value instanceof ApiError && [401, 403, 404].includes(value.status);
}
watch(
  () => inaccessible(detail.error.value) || inaccessible(list.error.value),
  (denied) => {
    if (denied) resetMutation();
  },
);
function manage(action: "rename" | "delete") {
  dialogTrigger = document.activeElement as HTMLElement | null;
  mutationError.value = "";
  notice.value = "";
  dialog.value = action;
}
async function mutate(action: "rename" | "archive" | "delete", title?: string) {
  const thread = detail.data.value;
  if (
    busy.value ||
    !allowed.value ||
    !thread ||
    inaccessible(detail.error.value) ||
    inaccessible(list.error.value)
  )
    return;
  if (action === "rename" && !title?.trim()) return;
  const trigger = dialogTrigger;
  const request = ++operation;
  const key = ["data", "research_threads", ...scope.value];
  busy.value = true;
  mutationError.value = "";
  notice.value = "";
  try {
    if (action === "delete") await researchThreadsApi.remove(thread.thread_id);
    else
      await researchThreadsApi.patch(
        thread.thread_id,
        action === "rename" ? { title: title?.trim() ?? "" } : { archived: !thread.archived_at },
      );
    if (request !== operation) return;
    dialog.value = null;
    if (action === "delete") {
      // Deletion clears the selected workspace, while cached answers/provenance follow their existing retention policy.
      client.setQueryData([...key, "thread", thread.thread_id], null);
      emit("removed");
    } else
      notice.value = i18n.t(
        action === "rename"
          ? "research.thread_renamed"
          : thread.archived_at
            ? "research.thread_unarchived"
            : "research.thread_archive_saved",
      );
    await client.invalidateQueries({ queryKey: key });
  } catch (error) {
    if (request !== operation) return;
    mutationError.value = error instanceof Error ? error.message : String(error);
    if (inaccessible(error)) {
      // The server owns authorization; never retain deleted or revoked thread shells after a failed mutation.
      client.setQueryData([...key, "thread", thread.thread_id], null);
      dialog.value = null;
      emit("removed", mutationError.value);
      void client.invalidateQueries({ queryKey: key });
    }
  } finally {
    if (request === operation) {
      busy.value = false;
      // The shared dialog unmounts while its trigger is still disabled during the save.
      // Restore focus after the updated navigation controls become operable again.
      if (action === "rename" && !dialog.value) {
        await nextTick();
        if (request === operation && trigger?.isConnected) trigger.focus({ preventScroll: true });
      }
    }
  }
}
function retry() {
  mutationError.value = "";
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
    :error="error || (!dialog ? mutationError : '')"
    :include-archived="includeArchived"
    :busy="busy"
    :notice="notice"
    @select="emit('select', $event)"
    @open="emit('open', $event)"
    @new="emit('new')"
    @page="offset = $event"
    @retry="retry"
    @include-archived="includeArchived = $event"
    @rename="manage('rename')"
    @archive="mutate('archive')"
    @remove="manage('delete')"
  >
    <template #answer="{ turn }">
      <ResearchThreadAnswer :key="turn.turn_id" :turn="turn" />
    </template>
  </ResearchThreadNavigation>
  <ResearchThreadManageDialog
    v-if="
      allowed &&
      dialog &&
      detail.data.value &&
      !inaccessible(detail.error.value) &&
      !inaccessible(list.error.value)
    "
    :key="threadId + dialog"
    :thread="detail.data.value"
    :action="dialog"
    :busy="busy"
    :error="mutationError"
    @close="dialog = null"
    @save="mutate('rename', $event)"
    @remove="mutate('delete')"
  />
</template>

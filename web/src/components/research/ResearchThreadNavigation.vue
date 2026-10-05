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
import { useI18nStore } from "../../stores/i18n";
import type {
  ResearchThreadDetail,
  ResearchThreadSummary,
  ResearchTurn,
} from "../../types/researchThreads";

defineProps<{
  threads: ResearchThreadSummary[];
  thread?: ResearchThreadDetail | null;
  selectedThreadId: string;
  selectedJobId?: string;
  offset: number;
  loading?: boolean;
  error?: string;
  includeArchived?: boolean;
  busy?: boolean;
  notice?: string;
}>();
const emit = defineEmits<{
  select: [id: string];
  open: [turn: ResearchTurn];
  new: [];
  page: [offset: number];
  retry: [];
  rename: [];
  archive: [];
  remove: [];
  includeArchived: [value: boolean];
}>();
const i18n = useI18nStore();
</script>

<template>
  <section class="research-thread-navigation" aria-labelledby="research-threads-title">
    <h2 id="research-threads-title">{{ i18n.t("research.threads_title") }}</h2>
    <button type="button" class="btn" @click="emit('new')">
      {{ i18n.t("research.thread_new") }}
    </button>
    <label class="research-thread-archive-filter">
      <input
        type="checkbox"
        :checked="includeArchived"
        @change="emit('includeArchived', ($event.target as HTMLInputElement).checked)"
      />
      {{ i18n.t("research.threads_include_archived") }}
    </label>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="loading || busy" role="status">{{ i18n.t("loading.updating") }}</p>
    <div v-if="error" role="alert">
      <p>{{ error }}</p>
      <button type="button" class="btn" @click="emit('retry')">{{ i18n.t("ui.retry") }}</button>
    </div>
    <nav :aria-label="i18n.t('research.threads_title')">
      <ul>
        <li v-for="item in threads" :key="item.thread_id">
          <button
            type="button"
            class="btn"
            :aria-current="selectedThreadId === item.thread_id ? 'true' : undefined"
            @click="emit('select', item.thread_id)"
          >
            {{ item.title }}
            <span v-if="item.archived_at">{{ i18n.t("research.thread_archived") }}</span>
            <span>{{ i18n.tf("research.thread_turn_count", { count: item.turn_count }) }}</span>
          </button>
        </li>
      </ul>
    </nav>
    <p v-if="!loading && !error && !threads.length">{{ i18n.t("research.threads_empty") }}</p>
    <div class="research-thread-pages">
      <button
        type="button"
        class="btn"
        :disabled="loading || offset === 0"
        @click="emit('page', Math.max(0, offset - 50))"
      >
        {{ i18n.t("research.threads_previous") }}
      </button>
      <button
        type="button"
        class="btn"
        :disabled="loading || threads.length < 50"
        @click="emit('page', offset + 50)"
      >
        {{ i18n.t("research.threads_next") }}
      </button>
    </div>
    <section v-if="thread" :aria-label="thread.title">
      <h3>{{ thread.title }}</h3>
      <p v-if="thread.archived_at">{{ i18n.t("research.thread_archived") }}</p>
      <div
        class="research-thread-management"
        :aria-label="i18n.t('research.thread_manage')"
        role="group"
      >
        <button class="btn" type="button" :disabled="busy" @click="emit('rename')">
          {{ i18n.t("research.thread_rename") }}
        </button>
        <button class="btn" type="button" :disabled="busy" @click="emit('archive')">
          {{ i18n.t(thread.archived_at ? "research.thread_unarchive" : "research.thread_archive") }}
        </button>
        <button class="btn" type="button" :disabled="busy" @click="emit('remove')">
          {{ i18n.t("research.thread_delete") }}
        </button>
      </div>
      <ol>
        <li v-for="turn in thread.turns" :key="turn.turn_id">
          <article :aria-labelledby="`heading-${turn.turn_id}`">
            <h4 :id="`heading-${turn.turn_id}`">{{ turn.user_question }}</h4>
            <p>{{ i18n.t(`research.thread_status_${turn.status}`) }}</p>
            <p v-if="turn.error" role="alert">{{ turn.error }}</p>
            <button
              v-if="turn.job_id"
              type="button"
              class="btn"
              :aria-current="selectedJobId === turn.job_id ? 'true' : undefined"
              @click="emit('open', turn)"
            >
              {{ i18n.t("research.thread_open_run") }}
            </button>
            <p v-else>{{ i18n.t("research.thread_run_unavailable") }}</p>
          </article>
        </li>
      </ol>
      <p>{{ i18n.t("research.thread_context_pending") }}</p>
    </section>
  </section>
</template>

<style scoped>
.research-thread-navigation {
  padding: var(--page-pad-inline);
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  margin-block: var(--page-gap);
  overflow-wrap: anywhere;
}
ul,
ol {
  display: grid;
  gap: calc(var(--page-gap) / 2);
  padding-inline-start: var(--page-pad-inline);
}
nav button {
  white-space: normal;
  text-align: start;
}
nav span {
  margin-inline-start: calc(var(--page-gap) / 2);
}
[aria-current="true"] {
  border-color: var(--accent-fg);
  font-weight: 700;
}
.research-thread-archive-filter {
  display: flex;
  align-items: center;
  gap: calc(var(--page-gap) / 2);
  margin-block: var(--page-gap);
}
.research-thread-pages,
.research-thread-management {
  display: flex;
  flex-wrap: wrap;
  gap: calc(var(--page-gap) / 2);
}
</style>

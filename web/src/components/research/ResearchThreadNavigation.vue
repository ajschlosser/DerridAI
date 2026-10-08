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
  search?: string;
  showPreview?: boolean;
  loading?: boolean;
  error?: string;
  includeArchived?: boolean;
  busy?: boolean;
  notice?: string;
  retryDisabled?: boolean;
}>();
const emit = defineEmits<{
  select: [id: string];
  open: [turn: ResearchTurn];
  new: [];
  page: [offset: number];
  search: [value: string];
  retry: [];
  retryTurn: [turn: ResearchTurn];
  rename: [];
  archive: [];
  remove: [];
  includeArchived: [value: boolean];
}>();
const i18n = useI18nStore();
</script>

<template>
  <section class="research-thread-navigation" aria-labelledby="research-threads-title">
    <h2 class="research-thread-index-title" id="research-threads-title">{{ i18n.t("research.threads_title") }}</h2>
    <button type="button" class="btn" @click="emit('new')">
      {{ i18n.t("research.thread_new") }}
    </button>
    <label>
      {{ i18n.t("research.threads_search") }}
      <input
        type="search"
        :value="search"
        maxlength="200"
        @input="emit('search', ($event.target as HTMLInputElement).value)"
      />
    </label>
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
    <nav class="research-thread-index" :aria-label="i18n.t('research.threads_title')">
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
            <span v-if="showPreview">{{ item.last_question }}</span>
            <time :datetime="item.updated_at">{{
              new Date(item.updated_at).toLocaleDateString(i18n.locale)
            }}</time>
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
    <section v-if="thread" class="research-thread-conversation" :aria-label="thread.title">
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
      <ol class="research-thread-turns">
        <li v-for="turn in thread.turns" :key="turn.turn_id">
          <article class="research-thread-turn" :aria-labelledby="`heading-${turn.turn_id}`">
            <h4 :id="`heading-${turn.turn_id}`">{{ turn.user_question }}</h4>
            <p class="research-thread-turn-status">{{ i18n.t(`research.thread_status_${turn.status}`) }}</p>
            <slot name="answer" :turn="turn" />
            <div v-if="['failed', 'cancelled'].includes(turn.status)">
              <p>{{ i18n.t("research.thread_retry_help") }}</p>
              <button
                class="btn"
                type="button"
                :disabled="
                  busy ||
                  loading ||
                  retryDisabled ||
                  Boolean(thread.archived_at) ||
                  thread.turns.some((item) => ['queued', 'running'].includes(item.status))
                "
                @click="emit('retryTurn', turn)"
              >
                {{ i18n.t("research.thread_retry") }}
              </button>
            </div>
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
    </section>
  </section>
</template>

<style scoped>
/* The index and conversation form separate reading regions rather than one vertical card. */
.research-thread-navigation {
  display: grid;
  grid-template-columns: minmax(230px, 270px) minmax(0, 1fr);
  grid-auto-flow: row;
  column-gap: var(--space-5, 20px);
  row-gap: var(--space-3, 12px);
  align-items: start;
  padding: var(--page-pad-inline);
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  margin-block: var(--page-gap);
  overflow-wrap: anywhere;
}
.research-thread-navigation > :not(.research-thread-conversation) {
  grid-column: 1;
  min-width: 0;
}
.research-thread-index-title {
  margin-block: 0;
}
.research-thread-navigation > button {
  justify-self: stretch;
}
.research-thread-navigation > label:not(.research-thread-archive-filter) {
  display: grid;
  gap: var(--space-2, 8px);
}
.research-thread-navigation input[type="search"] {
  min-width: 0;
  width: 100%;
}
.research-thread-index {
  min-width: 0;
  max-height: min(58vh, 650px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.research-thread-index ul {
  list-style: none;
  display: grid;
  gap: var(--space-2, 8px);
  padding: 0;
  margin: 0;
}
.research-thread-index li {
  min-width: 0;
}
.research-thread-index button {
  display: grid;
  justify-items: start;
  gap: 5px;
  width: 100%;
  min-height: 72px;
  padding: 12px;
  white-space: normal;
  text-align: start;
  overflow-wrap: anywhere;
}
.research-thread-index button span,
.research-thread-index time {
  font-size: .78rem;
  color: var(--text-tertiary);
  font-weight: 400;
}
.research-thread-index button[aria-current="true"] {
  border-color: var(--accent-fg);
  background: var(--soft);
  box-shadow: inset 3px 0 0 var(--accent-fg);
  font-weight: 700;
}
.research-thread-conversation {
  grid-column: 2;
  grid-row: 1 / span 16;
  min-width: 0;
  padding-inline: clamp(10px, 2vw, 28px);
  border-inline-start: 1px solid var(--border);
}
.research-thread-conversation h3 {
  font-size: clamp(1.25rem, 1.8vw, 1.65rem);
  line-height: 1.3;
  margin: 0 0 var(--space-2, 8px);
}
.research-thread-management {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  padding-block: var(--space-2, 8px) var(--space-4, 16px);
  border-bottom: 1px solid var(--border);
}
.research-thread-turns {
  list-style: none;
  display: grid;
  gap: var(--space-5, 20px);
  margin: var(--space-4, 16px) 0;
  padding: 0;
}
.research-thread-turn {
  min-width: 0;
  padding: clamp(14px, 2vw, 24px);
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.research-thread-turn h4 {
  max-width: 75ch;
  margin-block: 0 var(--space-3, 12px);
  line-height: 1.4;
}
.research-thread-turn-status {
  display: inline-block;
  margin-block: 0 var(--space-3, 12px);
  font-size: .78rem;
  color: var(--text-tertiary);
}
.research-thread-pages {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
}
.research-thread-archive-filter {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}
@media (max-width: 900px) {
  .research-thread-navigation {
    grid-template-columns: minmax(0, 1fr);
  }
  .research-thread-navigation > :not(.research-thread-conversation),
  .research-thread-conversation {
    grid-column: 1;
    grid-row: auto;
  }
  .research-thread-conversation {
    border-inline-start: none;
    border-top: 1px solid var(--border);
    padding: var(--space-4, 16px) 0 0;
  }
  .research-thread-index {
    max-height: 220px;
  }
  .research-thread-turn {
    padding: 14px;
  }
}
</style>

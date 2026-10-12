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
import { computed, nextTick, ref, watch } from "vue";
import type {
  ResearchThreadDetail,
  ResearchThreadSummary,
  ResearchTurn,
} from "../../types/researchThreads";

const props = defineProps<{
  threads: ResearchThreadSummary[];
  thread?: ResearchThreadDetail | null;
  selectedThreadId: string;
  selectedJobId?: string;
  offset: number;
  hasMore?: boolean;
  search?: string;
  showPreview?: boolean;
  loading?: boolean;
  error?: string;
  includeArchived?: boolean;
  busy?: boolean;
  notice?: string;
  retryDisabled?: boolean;
  /** Text of an answer already loaded in this browser, or null when not loaded. */
  answerText?: (turn: ResearchTurn) => string | null;
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
const listExpanded = ref(false);
// In-thread search reads only questions and answers already loaded; it never
// fetches further answers or audit payloads.
const turnQuery = ref("");
watch(
  () => props.thread?.thread_id,
  () => (turnQuery.value = ""),
);
const turnSearch = computed(() => {
  const term = turnQuery.value.trim().toLocaleLowerCase();
  const turns = props.thread?.turns || [];
  if (!term) return null;
  let unsearched = 0;
  const matches = new Set<string>();
  for (const turn of turns) {
    const answer = turn.status === "completed" ? (props.answerText?.(turn) ?? null) : "";
    if (answer === null) unsearched++;
    const text = [turn.user_question, turn.user_instructions || "", answer || ""].join("\n");
    if (text.toLocaleLowerCase().includes(term)) matches.add(turn.turn_id);
  }
  return { matches, total: turns.length, unsearched };
});
function clearTurnSearch(event: KeyboardEvent) {
  if (!turnQuery.value) return;
  event.stopPropagation();
  turnQuery.value = "";
}
const conversationHeading = ref<HTMLElement | null>(null);
const sidebar = ref<HTMLElement | null>(null);
// When a different thread loads after list selection or browser Back/Forward,
// move focus to its heading. Focus elsewhere (e.g. the composer) is left alone.
watch(
  () => props.thread?.thread_id || "",
  async (next, previous) => {
    if (!next || next === previous) return;
    const active = document.activeElement;
    const fromList = Boolean(active && sidebar.value?.contains(active));
    if (active && active !== document.body && !fromList) return;
    await nextTick();
    conversationHeading.value?.focus({ preventScroll: false });
  },
);
const manageExpanded = ref(false);
// Escape clears an active search first; an empty field lets Escape reach outer handlers.
function clearSearch(event: KeyboardEvent) {
  const input = event.target as HTMLInputElement;
  if (!input.value) return;
  event.stopPropagation();
  input.value = "";
  emit("search", "");
}
</script>

<template>
  <section
    class="research-thread-navigation"
    :class="{ 'research-thread-workspace-layout': Boolean($slots.workspace) }"
    aria-labelledby="research-threads-title"
  >
    <h2 class="research-thread-index-title" id="research-threads-title">
      {{ i18n.t("research.threads_title") }}
    </h2>
    <button
      type="button"
      class="btn research-thread-list-toggle"
      aria-controls="research-thread-sidebar"
      :aria-expanded="listExpanded"
      @click="listExpanded = !listExpanded"
    >
      {{ i18n.t("research.threads_title") }}
    </button>
    <div
      id="research-thread-sidebar"
      ref="sidebar"
      class="research-thread-sidebar"
      :class="{ 'is-expanded': listExpanded }"
    >
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
          @keydown.escape="clearSearch"
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
        <button type="button" class="btn" @click="emit('retry')">
          {{ i18n.t("ui.retry") }}
        </button>
      </div>
      <nav class="research-thread-index" :aria-label="i18n.t('research.threads_title')">
        <ul>
          <li v-for="item in threads" :key="item.thread_id">
            <button
              type="button"
              class="btn"
              :aria-current="selectedThreadId === item.thread_id ? 'true' : undefined"
              @click="
                emit('select', item.thread_id);
                listExpanded = false;
              "
            >
              <span class="research-thread-title">{{ item.title }}</span>
              <span v-if="item.archived_at">{{ i18n.t("research.thread_archived") }}</span>
              <span
                v-else-if="item.last_status && item.last_status !== 'completed'"
                :class="['research-thread-state', `is-${item.last_status}`]"
              >
                {{ i18n.t(`research.thread_status_${item.last_status}`) }}
              </span>
              <span class="research-thread-turn-count">{{
                i18n.tf("research.thread_turn_count", { count: item.turn_count })
              }}</span>
              <span v-if="showPreview && item.last_question" class="research-thread-preview">{{
                item.last_question
              }}</span>
              <time :datetime="item.updated_at">{{
                new Date(item.updated_at).toLocaleDateString(i18n.locale)
              }}</time>
            </button>
          </li>
        </ul>
      </nav>
      <p v-if="!loading && !error && !threads.length" role="status">
        {{
          search?.trim()
            ? i18n.tf("research.threads_no_match", { query: search.trim() })
            : i18n.t("research.threads_empty")
        }}
      </p>
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
          :disabled="loading || !hasMore"
          @click="emit('page', offset + 50)"
        >
          {{ i18n.t("research.threads_next") }}
        </button>
      </div>
    </div>
    <div class="research-thread-primary">
      <section
        v-if="thread"
        class="research-thread-conversation"
        :aria-label="thread.title"
        tabindex="-1"
      >
        <h2 ref="conversationHeading" tabindex="-1">{{ thread.title }}</h2>
        <p v-if="thread.archived_at">{{ i18n.t("research.thread_archived") }}</p>
        <details
          class="research-thread-management"
          :open="manageExpanded"
          @toggle="manageExpanded = ($event.target as HTMLDetailsElement).open"
        >
          <summary>{{ i18n.t("research.thread_manage") }}</summary>
          <div
            class="research-thread-management-actions"
            role="group"
            :aria-label="i18n.t('research.thread_manage')"
          >
            <button class="btn" type="button" :disabled="busy" @click="emit('rename')">
              {{ i18n.t("research.thread_rename") }}
            </button>
            <button class="btn" type="button" :disabled="busy" @click="emit('archive')">
              {{
                i18n.t(thread.archived_at ? "research.thread_unarchive" : "research.thread_archive")
              }}
            </button>
            <button class="btn" type="button" :disabled="busy" @click="emit('remove')">
              {{ i18n.t("research.thread_delete") }}
            </button>
          </div>
        </details>
        <div v-if="thread.turns.length > 1" class="research-thread-turn-search">
          <label>
            {{ i18n.t("research.thread_search") }}
            <input
              v-model="turnQuery"
              type="search"
              maxlength="200"
              @keydown.escape="clearTurnSearch"
            />
          </label>
          <p v-if="turnSearch" role="status">
            {{
              i18n.tf("research.thread_search_count", {
                shown: turnSearch.matches.size,
                total: turnSearch.total,
              })
            }}
            <template v-if="turnSearch.unsearched">
              {{ i18n.tf("research.thread_search_unsearched", { count: turnSearch.unsearched }) }}
            </template>
          </p>
        </div>
        <ol class="research-thread-turns">
          <li
            v-for="turn in thread.turns"
            v-show="!turnSearch || turnSearch.matches.has(turn.turn_id)"
            :key="turn.turn_id"
          >
            <article class="research-thread-turn" :aria-labelledby="`heading-${turn.turn_id}`">
              <h3 :id="`heading-${turn.turn_id}`">{{ turn.user_question }}</h3>
              <p class="research-thread-turn-status">
                {{ i18n.t(`research.thread_status_${turn.status}`) }}
              </p>
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
      <div v-if="$slots.workspace" class="research-thread-workspace">
        <slot name="workspace" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.research-thread-navigation {
  display: grid;
  grid-template-columns: minmax(230px, 270px) minmax(0, 1fr);
  column-gap: 20px;
  align-items: start;
  padding: var(--page-pad-inline);
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  margin-block: var(--page-gap);
  min-width: 0;
}
.research-thread-turn-search {
  display: grid;
  gap: 6px;
  margin-block: 8px 12px;
}
.research-thread-turn-search label {
  display: grid;
  gap: 4px;
}
.research-thread-index-title {
  grid-column: 1;
  margin: 0 0 12px;
}
.research-thread-list-toggle {
  display: none;
}
.research-thread-sidebar {
  grid-column: 1;
  display: grid;
  gap: 12px;
  min-width: 0;
}
.research-thread-sidebar > label:not(.research-thread-archive-filter) {
  display: grid;
  gap: 8px;
}
.research-thread-sidebar input[type="search"] {
  width: 100%;
  min-width: 0;
}
.research-thread-index {
  max-height: min(58vh, 650px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.research-thread-index ul {
  list-style: none;
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
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
  font-size: 0.78rem;
  color: var(--text-tertiary);
  font-weight: 400;
}
.research-thread-index button .research-thread-title {
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.35;
}
.research-thread-index button .research-thread-preview {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  line-height: 1.4;
}
.research-thread-index button .research-thread-state {
  font-weight: 650;
}
.research-thread-index button .research-thread-state.is-failed {
  color: var(--tone-danger-fg);
}
.research-thread-index button .research-thread-state.is-running {
  color: var(--accent-fg);
}
.research-thread-index button[aria-current="true"] {
  border-color: var(--accent-fg);
  background: var(--soft);
  box-shadow: inset 3px 0 0 var(--accent-fg);
  font-weight: 700;
}
.research-thread-primary {
  grid-column: 2;
  grid-row: 1 / span 3;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding-inline: clamp(10px, 2vw, 28px);
  border-inline-start: 1px solid var(--border);
}
.research-thread-conversation {
  flex: 1 1 auto;
  min-width: 0;
}
.research-thread-conversation > h2 {
  font-size: clamp(1.25rem, 1.8vw, 1.65rem);
  line-height: 1.3;
  margin: 0 0 8px;
  overflow-wrap: anywhere;
}
.research-thread-management {
  border-bottom: 1px solid var(--border);
  padding-block: 8px 16px;
}
.research-thread-management summary {
  cursor: pointer;
  width: fit-content;
  padding: 8px;
}
.research-thread-management-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 8px;
}
.research-thread-turns {
  list-style: none;
  display: grid;
  gap: 20px;
  margin: 16px 0;
  padding: 0;
}
.research-thread-turn {
  min-width: 0;
  padding: clamp(14px, 2vw, 24px);
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.research-thread-turn h3 {
  max-width: 75ch;
  margin-block: 0 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.research-thread-turn-status {
  display: inline-block;
  margin-block: 0 12px;
  font-size: 0.78rem;
  color: var(--text-tertiary);
}
.research-thread-pages,
.research-thread-archive-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
/* Research uses one coherent thread/list/composer surface. The Library can
   continue to render the browser on its own without this workspace slot. */
.research-thread-workspace-layout {
  min-height: min(72dvh, 760px);
}
.research-thread-workspace-layout .research-thread-sidebar {
  align-content: start;
}
.research-thread-workspace-layout .research-thread-primary {
  min-height: min(72dvh, 760px);
}
.research-thread-workspace-layout .research-thread-conversation {
  max-height: min(52dvh, 590px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-inline-end: 8px;
}
.research-thread-workspace {
  display: grid;
  gap: var(--page-gap);
  min-width: 0;
}
.research-thread-workspace :deep(.research-composer-followup) {
  position: static;
  inset: auto;
  transform: none;
  width: 100%;
  max-height: none;
  overflow: visible;
  pointer-events: auto;
  box-shadow: none;
}
@media (max-width: 900px) {
  .research-thread-navigation {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }
  .research-thread-index-title {
    display: none;
  }
  .research-thread-list-toggle {
    display: block;
    grid-column: 1;
    grid-row: 1;
    justify-self: start;
    position: relative;
    z-index: 42;
  }
  .research-thread-sidebar {
    display: none;
    grid-column: 1;
    grid-row: 2;
    max-height: 65vh;
    overflow: auto;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
  }
  .research-thread-sidebar.is-expanded {
    display: grid;
    position: relative;
    z-index: 41;
    background: var(--surface-card);
  }
  .research-thread-primary {
    grid-column: 1;
    grid-row: 3;
    border-inline-start: 0;
    padding: 12px 0 0;
  }
  .research-thread-workspace-layout .research-thread-primary {
    min-height: 0;
  }
  .research-thread-workspace-layout .research-thread-conversation {
    max-height: none;
    overflow: visible;
    padding-inline-end: 0;
  }
  .research-thread-index {
    max-height: 220px;
  }
  .research-thread-turn {
    padding: 14px;
  }
}
</style>

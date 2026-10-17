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
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { ResearchJob } from "../../types/research";
import { researchJobDetail } from "./researchI18n";
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
  /** Live job snapshots known to this browser; a turn without one shows only its status. */
  jobs?: ResearchJob[];
  canCancel?: boolean;
  /** A turn's evidence inspector is open: the list folds to a toggle so the
   * page shows two columns at most (threads + reading, or reading + source). */
  collapseList?: boolean;
}>();
const emit = defineEmits<{
  select: [id: string];
  open: [turn: ResearchTurn];
  new: [];
  page: [offset: number];
  search: [value: string];
  retry: [];
  retryTurn: [turn: ResearchTurn];
  cancelTurn: [job: ResearchJob];
  followUp: [turn: ResearchTurn];
  rename: [];
  archive: [];
  pin: [];
  remove: [];
  export: [format: "md" | "json"];
  includeArchived: [value: boolean];
}>();
const i18n = useI18nStore();
const listExpanded = ref(false);
watch(
  () => props.collapseList,
  () => {
    listExpanded.value = false;
  },
);
// The follow-up composer stays in view at the bottom of the reading column.
// Its height is exposed so focus moved into the conversation is not hidden
// behind it (WCAG 2.4.11).
const workspace = ref<HTMLElement | null>(null);
const workspaceBlockSize = ref(0);
let workspaceObserver: ResizeObserver | null = null;
watch(
  workspace,
  (element) => {
    workspaceObserver?.disconnect();
    workspaceObserver = null;
    if (!element || typeof ResizeObserver !== "function") return;
    workspaceObserver = new ResizeObserver(([entry]) => {
      workspaceBlockSize.value = Math.ceil(entry?.borderBoxSize?.[0]?.blockSize ?? 0);
    });
    workspaceObserver.observe(element);
  },
  { flush: "post" },
);
onBeforeUnmount(() => workspaceObserver?.disconnect());
// In-thread search reads only questions and answers already loaded; it never
// fetches further answers or audit payloads.
const turnQuery = ref("");
const compareOpen = ref(false);
watch(
  () => props.thread?.thread_id,
  () => {
    turnQuery.value = "";
    compareOpen.value = false;
  },
);
const completedTurns = computed(
  () => props.thread?.turns.filter((turn) => turn.status === "completed").length || 0,
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
// A queued/running turn reports its job's own stage, never an invented one.
function liveJob(turn: ResearchTurn) {
  if (!["queued", "running"].includes(turn.status) || !turn.job_id) return null;
  const job = props.jobs?.find((item) => item.id === turn.job_id);
  return job && ["queued", "running", "cancelling"].includes(job.status) ? job : null;
}
function turnStatusLabel(turn: ResearchTurn) {
  const job = liveJob(turn);
  if (job?.status === "cancelling" || job?.cancel_requested)
    return i18n.t("research.status_cancelling");
  return i18n.t(`research.thread_status_${turn.status}`);
}
function jobStage(job: ResearchJob) {
  return researchJobDetail(job, (key, fallback) => i18n.t(key, fallback), i18n.locale);
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
    :class="{
      'research-thread-workspace-layout': Boolean($slots.workspace),
      'is-list-collapsed': collapseList,
      'has-thread': Boolean(thread),
    }"
    :style="
      workspaceBlockSize
        ? { '--research-workspace-block-size': `${workspaceBlockSize}px` }
        : undefined
    "
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
              <span v-if="item.pinned_at" class="research-thread-pinned">{{
                i18n.t("research.thread_pinned")
              }}</span>
              <span v-if="item.archived_at">{{ i18n.t("research.thread_archived") }}</span>
              <span
                v-else-if="item.last_status && item.last_status !== 'completed'"
                :class="['research-thread-state', `is-${item.last_status}`]"
              >
                {{ i18n.t(`research.thread_status_${item.last_status}`) }}
              </span>
              <span
                v-if="showPreview && item.last_question && item.last_question !== item.title"
                class="research-thread-preview"
                >{{ item.last_question }}</span
              >
              <span class="research-thread-meta"
                ><span class="research-thread-turn-count">{{
                  i18n.tf(
                    item.turn_count === 1
                      ? "research.thread_turn_count_one"
                      : "research.thread_turn_count_other",
                    { count: item.turn_count },
                  )
                }}</span>
                <span aria-hidden="true">·</span>
                <time :datetime="item.last_asked_at ?? item.updated_at">{{
                  new Date(item.last_asked_at ?? item.updated_at).toLocaleDateString(i18n.locale)
                }}</time></span
              >
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
      <div v-if="offset > 0 || hasMore" class="research-thread-pages">
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
        <div class="research-thread-toolbar">
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
                  i18n.t(
                    thread.archived_at ? "research.thread_unarchive" : "research.thread_archive",
                  )
                }}
              </button>
              <button
                class="btn"
                type="button"
                :disabled="busy"
                :aria-pressed="thread.pinned_at ? 'true' : 'false'"
                @click="emit('pin')"
              >
                {{ i18n.t("research.thread_pin") }}
              </button>
              <button class="btn" type="button" :disabled="busy" @click="emit('remove')">
                {{ i18n.t("research.thread_delete") }}
              </button>
            </div>
            <div
              class="research-thread-export-actions"
              role="group"
              :aria-label="i18n.t('research.thread_export')"
            >
              <button class="btn" type="button" :disabled="busy" @click="emit('export', 'md')">
                {{ i18n.t("research.thread_export_markdown") }}
              </button>
              <button class="btn" type="button" :disabled="busy" @click="emit('export', 'json')">
                {{ i18n.t("research.thread_export_json") }}
              </button>
            </div>
          </details>
          <button
            v-if="completedTurns > 1 && $slots.compare && !compareOpen"
            type="button"
            class="btn research-thread-compare-toggle"
            @click="compareOpen = true"
          >
            {{ i18n.t("research.compare_turns") }}
          </button>
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
        </div>
        <slot
          v-if="compareOpen"
          name="compare"
          :turns="thread.turns"
          :close="() => (compareOpen = false)"
        />
        <ol class="research-thread-turns">
          <li
            v-for="turn in thread.turns"
            v-show="!turnSearch || turnSearch.matches.has(turn.turn_id)"
            :key="turn.turn_id"
          >
            <article class="research-thread-turn" :aria-labelledby="`heading-${turn.turn_id}`">
              <h3 :id="`heading-${turn.turn_id}`">{{ turn.user_question }}</h3>
              <div v-if="turn.status !== 'completed'" class="research-thread-turn-state">
                <p class="research-thread-turn-status">
                  <b>{{ turnStatusLabel(turn) }}</b>
                  <span v-if="liveJob(turn)">{{ jobStage(liveJob(turn)!) }}</span>
                  <span v-else-if="turn.error" role="alert">{{ turn.error }}</span>
                </p>
                <button
                  v-if="['failed', 'cancelled'].includes(turn.status)"
                  class="btn"
                  type="button"
                  :aria-describedby="`retry-help-${turn.turn_id}`"
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
                <button
                  v-else-if="canCancel && liveJob(turn)"
                  class="btn"
                  type="button"
                  :disabled="
                    liveJob(turn)!.status === 'cancelling' || liveJob(turn)!.cancel_requested
                  "
                  @click="emit('cancelTurn', liveJob(turn)!)"
                >
                  {{ i18n.t("research.cancel_run") }}
                </button>
                <p
                  v-if="['failed', 'cancelled'].includes(turn.status)"
                  :id="`retry-help-${turn.turn_id}`"
                  class="research-thread-turn-help"
                >
                  {{ i18n.t("research.thread_retry_help") }}
                </p>
              </div>
              <slot name="answer" :turn="turn" />
              <div class="research-thread-turn-actions">
                <!-- A completed turn's answer carries its own inspector toggle. -->
                <button
                  v-if="turn.job_id && turn.status !== 'completed'"
                  type="button"
                  class="btn"
                  :aria-current="selectedJobId === turn.job_id ? 'true' : undefined"
                  @click="emit('open', turn)"
                >
                  {{ i18n.t("research.thread_open_run") }}
                </button>
                <p v-else-if="!turn.job_id">{{ i18n.t("research.thread_run_unavailable") }}</p>
                <button
                  v-if="turn.status === 'completed' && !thread.archived_at && $slots.workspace"
                  type="button"
                  class="btn"
                  @click="emit('followUp', turn)"
                >
                  {{ i18n.t("research.thread_follow_up") }}
                </button>
              </div>
            </article>
          </li>
        </ol>
      </section>
      <div v-if="$slots.workspace" ref="workspace" class="research-thread-workspace">
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  margin-inline-start: auto;
}
.research-thread-turn-search label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
.research-thread-turn-search input {
  width: min(260px, 100%);
}
.research-thread-turn-search p {
  margin: 0;
  font-size: 0.8125rem;
}
/* Thread tools sit on one row under the title so the first answer is near
   the top; an opened panel takes its own full row. */
.research-thread-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding-block: 4px 14px;
  margin-block-end: 16px;
  border-bottom: 1px solid var(--border);
}
.research-thread-toolbar > .research-thread-management[open] {
  order: 10;
  flex-basis: 100%;
}
.research-thread-turn-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.research-thread-turn-actions > p {
  margin: 0;
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
.research-thread-index button .research-thread-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0 6px;
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
/* Tertiary text falls below 4.5:1 on the dark selected background. */
.research-thread-index
  button[aria-current="true"]
  span:not(.research-thread-state, .research-thread-title),
.research-thread-index button[aria-current="true"] time {
  color: var(--text-secondary);
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
  min-width: 0;
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
/* Status, stage or failure reason, and the turn's one action share a row. */
.research-thread-turn-state {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
  margin-block: 0 12px;
}
.research-thread-turn-status {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}
.research-thread-turn-help {
  flex-basis: 100%;
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-secondary);
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
/* The conversation flows with the page. A capped inner scroll box left about
   270px of answer visible above the composer at common laptop sizes. */
.research-thread-workspace-layout .research-thread-conversation {
  padding-inline-end: 8px;
}
/* Each turn is a size container so its answer/inspector split follows the
   turn's own width, not the viewport (the app sidebar and thread list take
   a large share of it). */
.research-thread-turns > li {
  container: thread-turn / inline-size;
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
/* With a thread open, the composer (and any run status beneath it) sticks to
   the bottom of the reading column while the conversation scrolls. Short or
   heavily zoomed viewports keep it in flow so it never covers most of the
   answer. */
@media (min-height: 560px) {
  .research-thread-workspace-layout.has-thread {
    --research-sticky-workspace: var(--research-workspace-block-size, 0px);
  }
  .research-thread-workspace-layout.has-thread .research-thread-workspace {
    position: sticky;
    bottom: 0;
    z-index: 5;
    max-height: min(40dvh, 380px);
    overflow-y: auto;
    padding-block: 8px max(8px, env(safe-area-inset-bottom));
    background: var(--surface-card);
    border-top: 1px solid var(--border);
  }
  .research-thread-workspace-layout.has-thread
    .research-thread-conversation
    :is(a, button, input, select, textarea, summary, [tabindex]) {
    scroll-margin-bottom: calc(var(--research-sticky-workspace) + 12px);
  }
}
/* An open inspector folds the thread list to its toggle, as on narrow
   screens, so the answer and its evidence keep the width. */
.research-thread-navigation.is-list-collapsed {
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
}
.is-list-collapsed .research-thread-index-title {
  display: none;
}
.is-list-collapsed .research-thread-list-toggle {
  display: block;
  grid-column: 1;
  grid-row: 1;
  justify-self: start;
}
.is-list-collapsed .research-thread-sidebar {
  display: none;
  grid-column: 1;
  grid-row: 2;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
}
.is-list-collapsed .research-thread-sidebar.is-expanded {
  display: grid;
}
.is-list-collapsed .research-thread-primary {
  grid-column: 1;
  grid-row: 3;
  border-inline-start: 0;
  padding-inline: 0;
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

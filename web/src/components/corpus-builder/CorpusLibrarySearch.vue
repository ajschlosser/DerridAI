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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  corpusCaptureApi,
  type GutenbergHit,
  type GutenbergStatus,
  type WikisourceHit,
  type WikisourceProject,
} from "../../api/corpus";
import { sortLanguageCodes } from "../../domain/languages";
import { followResource } from "../../realtime/follow";
import { useI18nStore } from "../../stores/i18n";
import { groupWikisourceHits } from "../../features/corpus-builder/domain/wikisourceGroups";
import AppIcon from "../AppIcon.vue";
import LibraryCatalogueStatus from "./LibraryCatalogueStatus.vue";
import LibraryResultList from "./LibraryResultList.vue";

/**
 * Find a text in Project Gutenberg or Wikisource and import it, without leaving the dialog: results appear as you
 * type, a Wikisource chapter offers its whole work, progress and errors show on the row and in the dialog, and a
 * successful import closes it.
 */
type Library = "gutenberg" | "wikisource";
const props = withDefaults(
  defineProps<{
    query: string;
    language?: string;
    gutenbergHits?: GutenbergHit[];
    wikisourceHits?: WikisourceHit[];
    gutenbergStatus?: GutenbergStatus | null;
    /** The query each library last answered, so an empty result is told apart from "not searched yet". */
    searched?: { gutenberg: string; wikisource: string };
    busy?: string;
    error?: string;
    /** `gutenberg:<id>` or `wikisource:<url>` while that result is being imported. */
    importing?: string;
    /** Increments after each successful import. */
    imported?: number;
    disabled?: boolean;
  }>(),
  {
    language: "en",
    gutenbergHits: () => [],
    wikisourceHits: () => [],
    gutenbergStatus: null,
    searched: () => ({ gutenberg: "", wikisource: "" }),
    busy: "",
    error: "",
    importing: "",
    imported: 0,
    disabled: false,
  },
);
const emit = defineEmits<{
  "update:query": [string];
  "update:language": [string];
  search: [Library];
  importGutenberg: [number];
  importWikisource: [string];
  refreshGutenbergStatus: [];
  refreshGutenbergCatalogue: [];
  updateGutenbergArchive: [action: "start" | "pause" | "resume" | "refetch"];
  close: [];
}>();
const i18n = useI18nStore();

/**
 * Wikisource projects offered, as Wikimedia's project list reports them through the API (never a list
 * fixed in the browser). Names come from the browser's locale data.
 */
const projects = ref<WikisourceProject[]>([]);
const projectsAuthoritative = ref(true);
async function loadProjects() {
  try {
    const info = (await corpusCaptureApi.sourceProviders()).items.find(
      (item) => item.provider === "wikisource",
    );
    if (info && "projects" in info) {
      projects.value = info.projects;
      projectsAuthoritative.value = info.projects_authoritative;
    }
  } catch {
    projectsAuthoritative.value = false;
  }
}
const LANGUAGES = computed(() => {
  const codes = projects.value.map((project) => project.code);
  if (!codes.includes(props.language)) codes.push(props.language);
  return sortLanguageCodes(codes, i18n.locale);
});
const EXAMPLES: Record<Library, string[]> = {
  gutenberg: ["Rousseau", "Plato", "Nietzsche", "Hegel"],
  wikisource: ["Rousseau", "Descartes", "Pascal", "Montaigne"],
};
const DEBOUNCE_MS = 350;

const dialog = ref<HTMLDialogElement | null>(null);
const input = ref<HTMLInputElement | null>(null);
const results = ref<InstanceType<typeof LibraryResultList> | null>(null);
const library = ref<Library>("gutenberg");
let debounce: number | undefined;
let stopFollowingGutenberg: (() => void) | undefined;

const languageNames = computed(() => {
  try {
    return new Intl.DisplayNames([i18n.locale || "en"], { type: "language" });
  } catch {
    return null;
  }
});
const languageName = (code: string) =>
  code === "mul"
    ? projects.value.find((project) => project.code === code)?.name || code
    : languageNames.value?.of(code) || code;
const host = computed(() => `${props.language}.wikisource.org`);

const catalogueReady = computed(() => Boolean(props.gutenbergStatus?.search_ready));
const collectionReady = computed(() => Boolean(props.gutenbergStatus?.ready));
const canSearch = computed(() => library.value === "wikisource" || catalogueReady.value);
const searching = computed(() => props.busy === library.value);
const trimmed = computed(() => props.query.trim());
const answeredQuery = computed(() => props.searched[library.value]);

const workGroups = computed(() => groupWikisourceHits(props.wikisourceHits));
const resultCount = computed(() =>
  library.value === "gutenberg" ? props.gutenbergHits.length : workGroups.value.length,
);
const showEmpty = computed(
  () =>
    !searching.value &&
    !props.error &&
    Boolean(answeredQuery.value) &&
    answeredQuery.value === trimmed.value &&
    resultCount.value === 0,
);
const showIdle = computed(() => !trimmed.value && resultCount.value === 0);

function formatNumber(value: number) {
  return new Intl.NumberFormat(i18n.locale || undefined).format(value);
}

// --- Searching -------------------------------------------------------------------------------------------------
function searchNow() {
  window.clearTimeout(debounce);
  if (!canSearch.value || props.disabled) return;
  emit("search", library.value);
}
function onInput(event: Event) {
  emit("update:query", (event.target as HTMLInputElement).value);
}
// Results follow the query as it is typed; Enter searches at once.
watch(
  () => [props.query, library.value, props.language] as const,
  ([query], previous) => {
    window.clearTimeout(debounce);
    const text = query.trim();
    if (text.length < 2 && text) return;
    const changedLibrary = previous && previous[1] !== library.value;
    const changedLanguage = previous && previous[2] !== props.language;
    if (!text) {
      if (props.searched[library.value]) emit("search", library.value);
      return;
    }
    if (text === props.searched[library.value] && !changedLanguage) return;
    debounce = window.setTimeout(searchNow, changedLibrary || changedLanguage ? 0 : DEBOUNCE_MS);
  },
);
// Text typed before the Project Gutenberg catalogue was ready is searched as soon as it is.
watch(canSearch, (ready) => {
  if (ready && trimmed.value && trimmed.value !== props.searched[library.value]) searchNow();
});
function useExample(example: string) {
  emit("update:query", example);
  void nextTick(() => {
    searchNow();
    input.value?.focus();
  });
}

// --- Tabs ------------------------------------------------------------------------------------------------------
const libraries: Library[] = ["gutenberg", "wikisource"];
function selectLibrary(next: Library, focus = false) {
  library.value = next;
  if (focus) void nextTick(() => document.getElementById(`library-tab-${next}`)?.focus());
}
function tabKeydown(event: KeyboardEvent) {
  const index = libraries.indexOf(library.value);
  let next = index;
  if (event.key === "ArrowRight") next = (index + 1) % libraries.length;
  else if (event.key === "ArrowLeft") next = (index - 1 + libraries.length) % libraries.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = libraries.length - 1;
  else return;
  event.preventDefault();
  selectLibrary(libraries[next], true);
}

// --- Keyboard through the results: ↓ from the search box, ↑/↓ between rows, Escape back to the box --------------
function resultButtons(): HTMLButtonElement[] {
  const list = results.value?.$el;
  if (!(list instanceof HTMLElement)) return [];
  return Array.from(list.querySelectorAll<HTMLButtonElement>("[data-result-primary]")).filter(
    (button) => !button.disabled,
  );
}
function focusFirstResult(event: KeyboardEvent) {
  const first = resultButtons()[0];
  if (!first) return;
  event.preventDefault();
  first.focus();
}
function resultsKeydown(event: KeyboardEvent) {
  const buttons = resultButtons();
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
  if (event.key === "ArrowDown" && index >= 0) {
    event.preventDefault();
    buttons[Math.min(buttons.length - 1, index + 1)]?.focus();
  } else if (event.key === "ArrowUp" && index >= 0) {
    event.preventDefault();
    if (index === 0) input.value?.focus();
    else buttons[index - 1]?.focus();
  }
}

// --- Lifecycle -------------------------------------------------------------------------------------------------
function close() {
  if (dialog.value?.open && typeof dialog.value.close === "function") dialog.value.close();
  emit("close");
}
watch(
  () => props.imported,
  (count, before) => {
    if (count > (before ?? 0)) close();
  },
);
onMounted(() => {
  emit("refreshGutenbergStatus");
  // The offline collection is background work, not a tracked job: follow its realtime
  // activity topic instead of polling on a timer (falls back to a slow poll only while
  // the socket is unavailable).
  stopFollowingGutenberg = followResource({
    topic: "activity:gutenberg",
    refresh: () => emit("refreshGutenbergStatus"),
  });
  void loadProjects();
  const element = dialog.value;
  if (element && !element.open) {
    if (typeof element.showModal === "function") element.showModal();
    else element.setAttribute("open", "");
  }
  void nextTick(() => input.value?.focus());
});
onBeforeUnmount(() => {
  window.clearTimeout(debounce);
  stopFollowingGutenberg?.();
});
</script>

<template>
  <dialog
    ref="dialog"
    class="library-search"
    aria-labelledby="library-search-title"
    @cancel.prevent="close"
  >
    <header class="ls-head">
      <h2 id="library-search-title">
        {{ i18n.t("pdf_corpus.search_library", "Search digital libraries") }}
      </h2>
      <button type="button" class="ls-close" :aria-label="i18n.t('common.close')" @click="close">
        <AppIcon name="close" />
      </button>
    </header>

    <div class="ls-controls">
      <div
        class="ls-tabs"
        role="tablist"
        :aria-label="i18n.t('pdf_corpus.search_library')"
        @keydown="tabKeydown"
      >
        <button
          v-for="item in libraries"
          :id="`library-tab-${item}`"
          :key="item"
          type="button"
          role="tab"
          class="ls-tab"
          aria-controls="library-panel"
          :aria-selected="library === item"
          :tabindex="library === item ? 0 : -1"
          @click="selectLibrary(item)"
        >
          {{
            item === "gutenberg"
              ? i18n.t("pdf_corpus.project_gutenberg")
              : i18n.t("pdf_corpus.wikisource")
          }}
        </button>
      </div>
      <form class="ls-search" role="search" @submit.prevent="searchNow">
        <span class="ls-search-icon" aria-hidden="true"><AppIcon name="search" /></span>
        <input
          ref="input"
          class="ls-input"
          autofocus
          type="search"
          autocomplete="off"
          spellcheck="false"
          :value="query"
          :placeholder="
            library === 'gutenberg'
              ? i18n.t('pdf_corpus.library.placeholder_gutenberg')
              : i18n.t('pdf_corpus.library.placeholder_wikisource')
          "
          :aria-label="
            library === 'gutenberg'
              ? i18n.t('pdf_corpus.gutenberg_search')
              : i18n.t('pdf_corpus.wikisource_search')
          "
          :aria-controls="resultCount ? 'library-results' : undefined"
          :disabled="disabled"
          @input="onInput"
          @keydown.down="focusFirstResult"
        />
        <span v-if="searching" class="ls-spinner" role="status">
          <span class="sr-only">{{ i18n.t("pdf_corpus.library.searching") }}</span>
        </span>
        <select
          v-if="library === 'wikisource'"
          class="ls-language"
          :value="language"
          :aria-label="i18n.t('pdf_corpus.library.language_label')"
          :title="i18n.t('pdf_corpus.library.language_label')"
          @change="emit('update:language', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="code in LANGUAGES" :key="code" :value="code">
            {{ languageName(code) }}
          </option>
        </select>
      </form>
      <p class="ls-hint">
        {{
          library === "gutenberg"
            ? catalogueReady
              ? i18n.t("pdf_corpus.library.hint_gutenberg")
              : i18n.t("pdf_corpus.library.catalogue_needed")
            : i18n.tf("pdf_corpus.library.hint_wikisource", { host })
        }}
        <template v-if="library === 'wikisource' && !projectsAuthoritative">
          {{ i18n.t("pdf_corpus.library.projects_fallback") }}</template
        >
      </p>
      <p class="ls-hint">{{ i18n.t("pdf_corpus.library.capture_hint") }}</p>
    </div>

    <div
      id="library-panel"
      class="ls-body"
      role="tabpanel"
      :aria-labelledby="`library-tab-${library}`"
    >
      <p v-if="error" class="ls-error" role="alert">
        <AppIcon name="warning" /><span>{{ error }}</span>
      </p>

      <LibraryCatalogueStatus
        v-if="library === 'gutenberg' && (!catalogueReady || !collectionReady)"
        :status="gutenbergStatus"
        :catalogue-ready="catalogueReady"
        :disabled="disabled"
        :busy="busy"
        @refresh-catalogue="emit('refreshGutenbergCatalogue')"
        @update-archive="emit('updateGutenbergArchive', $event)"
      />

      <LibraryResultList
        v-if="resultCount"
        id="library-results"
        ref="results"
        :library="library"
        :gutenberg-hits="gutenbergHits"
        :work-groups="workGroups"
        :searching="searching"
        :collection-ready="collectionReady"
        :disabled="disabled"
        :importing="importing"
        :language-name="languageName"
        @keydown="resultsKeydown"
        @import-gutenberg="emit('importGutenberg', $event)"
        @import-wikisource="emit('importWikisource', $event)"
      />

      <p v-else-if="showEmpty" class="ls-empty">
        {{ i18n.tf("pdf_corpus.library.no_results", { query: answeredQuery }) }}
      </p>
      <div v-else-if="showIdle && canSearch" class="ls-idle">
        <span>{{ i18n.t("pdf_corpus.library.try_examples") }}</span>
        <button
          v-for="example in EXAMPLES[library]"
          :key="example"
          type="button"
          class="ls-chip"
          :disabled="disabled"
          @click="useExample(example)"
        >
          {{ example }}
        </button>
      </div>
    </div>

    <footer class="ls-foot">
      <span class="ls-count" aria-live="polite">{{
        resultCount && answeredQuery
          ? i18n.tf("pdf_corpus.library.results_count", { count: formatNumber(resultCount) })
          : ""
      }}</span>
      <button type="button" class="btn" @click="close">
        {{ i18n.t("common.close", "Close") }}
      </button>
    </footer>
  </dialog>
</template>

<style scoped>
.library-search {
  display: flex;
  flex-direction: column;
  inline-size: min(760px, calc(100vw - 32px));
  block-size: min(680px, calc(100dvh - 32px));
  margin: auto;
  padding: 0;
  border: 1px solid var(--border-strong, var(--line));
  border-radius: var(--radius-overlay, 16px);
  color: var(--text);
  background: var(--surface-overlay, var(--card));
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.library-search:not([open]) {
  display: none;
}
/* The dialog never scrolls as a whole: only its result list does, so the search box stays put. */
.library-search[open] {
  overflow: hidden;
  scrollbar-gutter: auto;
}
.library-search::backdrop {
  background: rgb(8 12 20 / 60%);
}
.ls-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 0;
}
.ls-head h2 {
  margin: 0;
  font-size: var(--fs-lg);
  letter-spacing: -0.01em;
}
.ls-close {
  display: inline-grid;
  place-items: center;
  inline-size: 36px;
  block-size: 36px;
  border: 0;
  border-radius: var(--radius-control);
  color: var(--text-secondary, var(--muted));
  background: transparent;
  cursor: pointer;
}
.ls-close:hover {
  background: var(--surface-hover);
}
.ls-controls {
  display: grid;
  gap: 10px;
  padding: 14px 20px 12px;
  border-bottom: 1px solid var(--border-subtle, var(--line));
}
.ls-tabs {
  display: inline-flex;
  justify-self: start;
  gap: 2px;
  padding: 3px;
  border-radius: 999px;
  background: var(--surface-inset, var(--soft));
}
.ls-tab {
  min-height: 32px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  color: var(--text-secondary, var(--muted));
  background: transparent;
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: 700;
  cursor: pointer;
}
.ls-tab[aria-selected="true"] {
  color: var(--text);
  background: var(--surface-card, var(--card));
  box-shadow: var(--shadow-card, 0 1px 2px rgb(0 0 0 / 10%));
}
.ls-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ls-search-icon {
  position: absolute;
  inset-inline-start: 12px;
  display: inline-flex;
  color: var(--text-tertiary, var(--muted));
  pointer-events: none;
}
.ls-search-icon :deep(svg) {
  inline-size: 18px;
  block-size: 18px;
}
.ls-input {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 44px;
  padding: 0 40px 0 40px;
  border: 1px solid var(--border-interactive, var(--line));
  border-radius: var(--radius-control);
  color: var(--text);
  background: var(--surface-card, var(--card));
  font: inherit;
  font-size: var(--fs-md);
}
.ls-input:focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 1px;
}
.ls-spinner {
  position: absolute;
  inset-inline-end: 12px;
  inline-size: 16px;
  block-size: 16px;
  border: 2px solid var(--border-subtle, var(--line));
  border-top-color: var(--accent-fg, var(--accent));
  border-radius: 50%;
  animation: ls-spin 0.8s linear infinite;
}
.ls-search:has(.ls-language) .ls-spinner {
  inset-inline-end: calc(12px + 11rem);
}
.ls-language {
  flex: none;
  inline-size: 10.5rem;
  min-height: 44px;
  padding: 0 10px;
  border: 1px solid var(--border-interactive, var(--line));
  border-radius: var(--radius-control);
  color: var(--text);
  background: var(--surface-card, var(--card));
  font: inherit;
  font-size: var(--fs-sm);
}
.ls-hint {
  margin: 0;
  color: var(--text-tertiary, var(--muted));
  font-size: var(--fs-sm);
}
.ls-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 12px 20px;
}
.ls-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 10px;
  padding: 8px 10px;
  border: 1px solid var(--tone-danger-border);
  border-radius: var(--radius-control);
  color: var(--tone-danger-fg);
  background: var(--tone-danger-bg);
  font-size: var(--fs-sm);
}
.ls-error :deep(svg) {
  flex: none;
  inline-size: 16px;
  block-size: 16px;
  margin-top: 1px;
}
.btn.quiet {
  border-color: transparent;
  background: transparent;
}
.btn.quiet:hover:not(:disabled) {
  background: var(--surface-hover);
}
.ls-empty {
  margin: 24px 0;
  color: var(--text-secondary, var(--muted));
  text-align: center;
}
.ls-idle {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 28px 0;
  color: var(--text-tertiary, var(--muted));
  font-size: var(--fs-sm);
}
.ls-chip {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--border-interactive, var(--line));
  border-radius: 999px;
  color: var(--text-secondary, var(--text));
  background: var(--surface-card, var(--card));
  font: inherit;
  font-size: var(--fs-sm);
  cursor: pointer;
}
.ls-chip:hover:not(:disabled) {
  border-color: var(--accent-fg, var(--accent));
  color: var(--accent-fg, var(--accent));
}
.ls-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid var(--border-subtle, var(--line));
}
.ls-count {
  color: var(--text-tertiary, var(--muted));
  font-size: var(--fs-sm);
}
:is(button, select, .ls-chip):focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
@keyframes ls-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ls-spinner {
    animation-duration: 2.4s;
  }
}
@media (max-width: 560px) {
  .ls-search {
    flex-wrap: wrap;
  }
  .ls-language {
    inline-size: 100%;
  }
  .ls-search:has(.ls-language) .ls-spinner {
    inset-inline-end: 12px;
    inset-block-start: 14px;
  }
}
</style>

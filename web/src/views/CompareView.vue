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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { copyCitation, copyJsonToClipboard } from "../domain/clipboardCopy";
import {
  ensureCompareLibrary,
  getCompareLibrary,
  getCompareRecord,
} from "../domain/sharedCompareLibrary";
import { useAuthStore } from "../stores/auth";
import { useCompareStore, useRecordViewStore } from "../stores/workspace";
import { state as sharedState } from "../domain/sharedUrlState";
import { corpusState } from "../state/workspaceState";
import { useI18nStore } from "../stores/i18n";
import { useNewerData } from "../composables/useNewerData";
import {
  loadCompareDraft,
  saveCompareDraft,
  type CompareDraft,
} from "../features/compare/compareDraft";
import NewerDataBanner from "../components/ui/NewerDataBanner.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import UiCard from "../components/ui/UiCard.vue";
import UiStatusBadge from "../components/ui/UiStatusBadge.vue";
import UiTabs from "../components/ui/UiTabs.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import ComparePicker from "../components/compare/ComparePicker.vue";
import CompareDiff from "../components/compare/CompareDiff.vue";
import {
  buildCompareRows,
  humanizeField,
  parseCompareRecord,
  prettyRecord,
  type CompareFilter,
  type CompareLibraryOption,
  type CompareSource,
} from "../domain/compare";

const auth = useAuthStore();
const i18n = useI18nStore();
// The Compare fields live in the compare store; the researcher's picks are in the record-view store.
const compare = useCompareStore();
const recordView = useRecordViewStore();
const workspace = compare as unknown as {
  compareA: string;
  compareB: string;
  compareMode: string;
  comparePasteA: string;
  comparePasteB: string;
  compareSourceA?: string;
  compareSourceB?: string;
  compareFilter?: string;
};
const library = ref<CompareLibraryOption[]>([]);
const libraryLoading = ref(true);
const libraryError = ref("");
let libraryRequest = 0;
const sourceA = ref<CompareSource>(
  workspace.compareSourceA === "scratch" || workspace.compareMode === "paste"
    ? "scratch"
    : "library",
);
const sourceB = ref<CompareSource>(
  workspace.compareSourceB === "scratch" || workspace.compareMode === "paste"
    ? "scratch"
    : "library",
);
const keyA = ref(
  auth.isResearcher ? recordView.researcherCompareA || "" : workspace.compareA || "",
);
const keyB = ref(
  auth.isResearcher ? recordView.researcherCompareB || "" : workspace.compareB || "",
);
const pasteA = ref(workspace.comparePasteA || "");
const pasteB = ref(workspace.comparePasteB || "");
const filter = ref<CompareFilter>(workspace.compareFilter === "all" ? "all" : "changed");
const liveMessage = ref("");
let draftTimer = 0;

function compareDraft(): CompareDraft {
  return {
    sourceA: sourceA.value,
    sourceB: sourceB.value,
    keyA: keyA.value,
    keyB: keyB.value,
    pasteA: pasteA.value,
    pasteB: pasteB.value,
    filter: filter.value,
  };
}
const initialDraft = compareDraft();

const parsedA = computed(() =>
  sourceA.value === "scratch"
    ? parseCompareRecord(pasteA.value)
    : {
        record: getCompareRecord(keyA.value)?.record || null,
        errorKey: "",
        errorFallback: "",
      },
);
const parsedB = computed(() =>
  sourceB.value === "scratch"
    ? parseCompareRecord(pasteB.value)
    : {
        record: getCompareRecord(keyB.value)?.record || null,
        errorKey: "",
        errorFallback: "",
      },
);
const recordA = computed(() => parsedA.value.record);
const recordB = computed(() => parsedB.value.record);
const allRows = computed(() => buildCompareRows(recordA.value, recordB.value, "all"));
const rows = computed(() =>
  (filter.value === "changed" ? allRows.value.filter((row) => row.changed) : allRows.value).map(
    (row) => ({
      ...row,
      label: i18n.t(`field.${row.key}`, humanizeField(row.key)),
    }),
  ),
);
const changedCount = computed(() => allRows.value.filter((row) => row.changed).length);
const totalCount = computed(() => allRows.value.length);
const ready = computed(() => Boolean(recordA.value && recordB.value));
const comparisonPending = computed(
  () =>
    !ready.value &&
    libraryLoading.value &&
    (sourceA.value === "library" || sourceB.value === "library"),
);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function persist() {
  if (auth.isResearcher) {
    recordView.researcherCompareA = keyA.value;
    recordView.researcherCompareB = keyB.value;
  } else {
    workspace.compareA = keyA.value;
    workspace.compareB = keyB.value;
  }
  workspace.comparePasteA = pasteA.value;
  workspace.comparePasteB = pasteB.value;
  workspace.compareSourceA = sourceA.value;
  workspace.compareSourceB = sourceB.value;
  workspace.compareFilter = filter.value;
  workspace.compareMode =
    sourceA.value === "scratch" && sourceB.value === "scratch" ? "paste" : "workspace";
  window.clearTimeout(draftTimer);
  const draft = compareDraft();
  draftTimer = window.setTimeout(() => void saveCompareDraft(draft), 300);
}
function refreshLibrary() {
  library.value = getCompareLibrary();
}

async function loadLibrary() {
  const request = ++libraryRequest;
  libraryLoading.value = true;
  libraryError.value = "";
  try {
    await ensureCompareLibrary();
    if (request !== libraryRequest) return;
    refreshLibrary();
  } catch (error) {
    if (request !== libraryRequest) return;
    libraryError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (request === libraryRequest) libraryLoading.value = false;
  }
}
function loadIntoEditor(side: "A" | "B") {
  const key = side === "A" ? keyA.value : keyB.value;
  const found = getCompareRecord(key);
  if (!found?.record) return;
  const text = prettyRecord(found.record);
  if (side === "A") {
    pasteA.value = text;
    sourceA.value = "scratch";
  } else {
    pasteB.value = text;
    sourceB.value = "scratch";
  }
  liveMessage.value = t("compare.loaded_editor", "Loaded the selected record into the editor.");
  persist();
}
function pretty(side: "A" | "B") {
  const parsed = side === "A" ? parsedA.value : parsedB.value;
  if (!parsed.record) return;
  if (side === "A") pasteA.value = prettyRecord(parsed.record);
  else pasteB.value = prettyRecord(parsed.record);
  persist();
}
function swapSides() {
  const next = {
    sourceA: sourceB.value,
    sourceB: sourceA.value,
    keyA: keyB.value,
    keyB: keyA.value,
    pasteA: pasteB.value,
    pasteB: pasteA.value,
  };
  sourceA.value = next.sourceA;
  sourceB.value = next.sourceB;
  keyA.value = next.keyA;
  keyB.value = next.keyB;
  pasteA.value = next.pasteA;
  pasteB.value = next.pasteB;
  liveMessage.value = t("compare.swapped", "Columns A and B were swapped.");
  persist();
}
function copyAtoB() {
  sourceB.value = sourceA.value;
  keyB.value = keyA.value;
  pasteB.value = sourceA.value === "scratch" ? pasteA.value : prettyRecord(recordA.value);
  if (sourceA.value === "library") sourceB.value = "scratch";
  liveMessage.value = t(
    "compare.copied_a_to_b",
    "Copied column A into column B as an editable copy.",
  );
  persist();
}
function copyJson(side: "A" | "B") {
  const record = side === "A" ? recordA.value : recordB.value;
  if (record) void copyJsonToClipboard(record, record.record_id || (side === "A" ? "A" : "B"));
}
function cite(side: "A" | "B", kind: "inline" | "full") {
  const record = side === "A" ? recordA.value : recordB.value;
  if (record) void copyCitation(record, kind);
}
function statusFor(side: "A" | "B") {
  const parsed = side === "A" ? parsedA.value : parsedB.value;
  const source = side === "A" ? sourceA.value : sourceB.value;
  const key = side === "A" ? keyA.value : keyB.value;
  if (source === "library") {
    if (libraryLoading.value && key)
      return { tone: "neutral" as const, label: i18n.t("ui.loading") };
    return parsed.record
      ? { tone: "success" as const, label: t("compare.status.library", "Library record") }
      : { tone: "warning" as const, label: t("compare.status.pick", "Pick a record") };
  }
  if (!(side === "A" ? pasteA.value : pasteB.value).trim())
    return { tone: "neutral" as const, label: t("compare.editor_empty", "Empty editor") };
  if (parsed.errorKey)
    return { tone: "danger" as const, label: t(parsed.errorKey, parsed.errorFallback) };
  return { tone: "success" as const, label: t("compare.editor_valid", "Valid JSON") };
}

watch([sourceA, sourceB, keyA, keyB, pasteA, pasteB, filter], persist);
// The picker searches the library read here. Records loaded or edited while Compare is open used to be missing from it
// until you left the view and came back, so read it again whenever the loaded corpus changes.
watch(() => [corpusState.version, corpusState.activeFileId], refreshLibrary, { flush: "post" });
const newer = useNewerData();
// ensureCompareLibrary only loads when the store page is empty, so clear it to read the new data.
async function loadNewer() {
  newer.acknowledge();
  sharedState.storeRecords = [];
  await loadLibrary();
}
onMounted(() => {
  void loadLibrary();
  void loadCompareDraft().then((saved) => {
    if (!saved) return;
    // Do not let a delayed IndexedDB read overwrite editing that began while
    // the page was becoming interactive.
    if (JSON.stringify(compareDraft()) !== JSON.stringify(initialDraft)) return;
    sourceA.value = saved.sourceA;
    sourceB.value = saved.sourceB;
    keyA.value = saved.keyA;
    keyB.value = saved.keyB;
    pasteA.value = saved.pasteA;
    pasteB.value = saved.pasteB;
    filter.value = saved.filter;
  });
});
onBeforeUnmount(() => {
  ++libraryRequest;
  window.clearTimeout(draftTimer);
});
</script>
<template>
  <main class="compare-page" aria-labelledby="compare-title">
    <NewerDataBanner :visible="newer.hasNewer.value" @load="loadNewer" />
    <p class="sr-only" aria-live="polite">{{ liveMessage }}</p>
    <UiPageHeader
      :kicker="t('section.corpora', 'Corpora')"
      :title="t('nav.compare', 'Compare')"
      title-id="compare-title"
      :description="
        auth.isResearcher
          ? t(
              'research.compare_help',
              'Compare researcher-visible summarized records side by side.',
            )
          : t(
              'compare.page_help',
              'Compare record metadata and text with focused, side-by-side field differences.',
            )
      "
      :actions-label="t('compare.page_actions', 'Compare actions')"
    >
      <template #actions>
        <UiButton :label="t('compare.swap', 'Swap A and B')" icon="compare" @click="swapSides" />
        <UiButton
          :label="t('compare.copy_a_to_b', 'Copy A into B')"
          :disabled="!recordA"
          :disabled-reason="t('compare.need_a', 'Select or paste record A first.')"
          @click="copyAtoB"
        />
      </template>
    </UiPageHeader>

    <p v-if="auth.isResearcher" class="compare-note">
      {{
        t(
          "compare.researcher_source_help",
          "Records are drawn from the selected corpus database and use the same Compare workspace as administrator accounts. Editing controls appear only where your role permits them.",
        )
      }}
    </p>

    <div class="compare-panes">
      <UiCard
        v-for="side in ['A', 'B'] as const"
        :key="side"
        class="compare-pane"
        :heading-id="`compare-pane-${side}`"
      >
        <div class="compare-pane-head">
          <div>
            <p class="compare-kicker">
              {{
                side === "A" ? t("compare.record_a", "Record A") : t("compare.record_b", "Record B")
              }}
            </p>
            <h2 :id="`compare-pane-${side}`">
              {{
                String(
                  (side === "A" ? recordA : recordB)?.work ||
                    (side === "A" ? recordA : recordB)?.record_id ||
                    t("compare.untitled", "Untitled record"),
                )
              }}
            </h2>
            <p>
              {{
                String(
                  (side === "A" ? recordA : recordB)?.document_author ||
                    t("compare.unknown_author", "Unknown author"),
                )
              }}
            </p>
          </div>
          <UiStatusBadge v-bind="statusFor(side)" />
        </div>
        <UiTabs
          :id-prefix="`compare-source-${side}`"
          :tablist-label="t('compare.source_label', 'Record source')"
          :tabs="[
            { id: 'library', label: t('compare.library', 'From library') },
            { id: 'scratch', label: t('compare.scratch', 'Editable copy') },
          ]"
          :model-value="side === 'A' ? sourceA : sourceB"
          @update:model-value="
            (value) =>
              side === 'A' ? (sourceA = value as CompareSource) : (sourceB = value as CompareSource)
          "
        />
        <div
          :id="`compare-source-${side}-panel-library`"
          role="tabpanel"
          :hidden="(side === 'A' ? sourceA : sourceB) !== 'library'"
        >
          <UiLoadingState
            v-if="libraryLoading"
            :variant="library.length ? 'inline' : 'skeleton'"
            :label="i18n.t(library.length ? 'loading.updating' : 'ui.loading')"
          />
          <div v-if="libraryError" class="info error compare-library-error" role="alert">
            <span>{{ libraryError }}</span>
            <UiButton size="small" :label="i18n.t('ui.retry')" @click="loadLibrary" />
          </div>
          <ComparePicker
            :model-value="side === 'A' ? keyA : keyB"
            :options="library"
            :label="t('compare.search_label', 'Find a loaded record')"
            :placeholder="t('compare.picker_placeholder', 'Type record ID, work, author, or file…')"
            :selected-hint="t('compare.selected', 'Selected · {label}')"
            :empty-hint="
              libraryLoading && !library.length
                ? i18n.t('ui.loading')
                : libraryError && !library.length
                  ? libraryError
                  : library.length
                    ? t('compare.library_help', 'Start typing to search loaded records.')
                    : t(
                        'compare.library_empty',
                        'Load JSONL files or browse the corpus database first.',
                      )
            "
            :no-matches="t('compare.no_matches', 'No matching records.')"
            :clear-label="t('ui.clear', 'Clear')"
            @update:model-value="(value) => (side === 'A' ? (keyA = value) : (keyB = value))"
          />
          <UiButton
            :label="t('compare.load_into_editor', 'Load into editor')"
            :disabled="!(side === 'A' ? keyA : keyB)"
            :disabled-reason="t('compare.need_library', 'Choose a library record first.')"
            @click="loadIntoEditor(side)"
          />
        </div>
        <div
          :id="`compare-source-${side}-panel-scratch`"
          role="tabpanel"
          :hidden="(side === 'A' ? sourceA : sourceB) !== 'scratch'"
        >
          <p class="compare-scratch-help">
            {{
              t(
                "compare.scratch_help",
                "Paste JSON or a single JSONL line. You can also load any library record here and edit the copy.",
              )
            }}
          </p>
          <label class="sr-only" :for="`compare-editor-${side}`">{{
            side === "A" ? t("compare.record_a", "Record A") : t("compare.record_b", "Record B")
          }}</label>
          <textarea
            :id="`compare-editor-${side}`"
            class="compare-editor"
            spellcheck="false"
            :placeholder="t('compare.editor_placeholder', 'Paste one JSON object or JSONL line')"
            :value="side === 'A' ? pasteA : pasteB"
            @input="
              side === 'A'
                ? (pasteA = ($event.target as HTMLTextAreaElement).value)
                : (pasteB = ($event.target as HTMLTextAreaElement).value)
            "
          />
          <div class="compare-editor-actions">
            <UiButton
              :label="t('compare.pretty_print', 'Format JSON')"
              size="small"
              :disabled="!(side === 'A' ? parsedA : parsedB).record"
              @click="pretty(side)"
            />
            <UiButton
              :label="t('compare.copy_json', 'Copy JSON')"
              size="small"
              :disabled="!(side === 'A' ? recordA : recordB)"
              @click="copyJson(side)"
            />
            <UiButton
              :label="t('ui.copy_inline', 'Inline citation')"
              size="small"
              :disabled="!(side === 'A' ? recordA : recordB)"
              @click="cite(side, 'inline')"
            />
            <UiButton
              :label="t('ui.copy_full', 'Full citation')"
              size="small"
              :disabled="!(side === 'A' ? recordA : recordB)"
              @click="cite(side, 'full')"
            />
          </div>
        </div>
      </UiCard>
    </div>

    <section class="compare-board" aria-labelledby="compare-board-title">
      <div class="compare-board-head">
        <div>
          <h2 id="compare-board-title">{{ t("compare.diff_title", "Field differences") }}</h2>
          <p>
            {{
              t(
                "compare.diff_help",
                "Provenance fields stay intact. Audit history is hidden so copies can be compared without noise.",
              )
            }}
          </p>
        </div>
        <div v-if="ready" class="compare-stats" aria-live="polite">
          <span
            ><strong>{{ changedCount }}</strong> {{ t("compare.fields_changed", "changed") }}</span
          >
          <span
            ><strong>{{ totalCount - changedCount }}</strong>
            {{ t("compare.fields_identical", "identical") }}</span
          >
          <span
            ><strong>{{ totalCount }}</strong> {{ t("compare.fields_compared", "compared") }}</span
          >
        </div>
      </div>
      <fieldset v-if="ready" class="compare-filter">
        <legend>{{ t("compare.filter_label", "Show") }}</legend>
        <label
          ><input v-model="filter" type="radio" value="changed" />
          {{ t("compare.diff_changed", "Differences only") }}</label
        >
        <label
          ><input v-model="filter" type="radio" value="all" />
          {{ t("compare.diff_all", "All fields") }}</label
        >
      </fieldset>
      <UiLoadingState v-if="comparisonPending" variant="skeleton" :label="i18n.t('ui.loading')" />
      <div v-else-if="!ready" class="compare-empty">
        <b>{{ t("compare.need_two", "Two records are needed") }}</b>
        <span>{{
          auth.isResearcher
            ? t(
                "compare.need_two_help",
                "Browse records or run a search first, then return to Compare.",
              )
            : t(
                "compare.need_two_admin",
                "Pick two library records, or load one into the editor and paste a copy beside it.",
              )
        }}</span>
      </div>
      <CompareDiff
        v-else
        :rows="rows"
        :empty-label="
          filter === 'changed'
            ? t('compare.diff_identical', 'These records are identical across all compared fields.')
            : t('compare.diff_empty', 'No fields to compare.')
        "
        :changed-label="t('compare.status.changed', 'Changed')"
        :identical-label="t('compare.status.identical', 'Identical')"
        :side-a="t('compare.record_a', 'Record A')"
        :side-b="t('compare.record_b', 'Record B')"
      />
    </section>
  </main>
</template>
<style scoped>
.compare-page {
  display: grid;
  gap: var(--page-gap);
}
.compare-board-head,
.compare-pane-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.compare-kicker {
  margin: 0 0 4px;
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-fg);
}
h2 {
  margin: 0;
  font-size: 1.15rem;
  line-height: 1.3;
}
.compare-note,
.compare-scratch-help,
.compare-empty span {
  margin: 6px 0 0;
  max-width: 70ch;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.compare-library-error {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.compare-editor-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.compare-note,
.compare-empty {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
}
.compare-panes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}
.compare-pane {
  display: grid;
  gap: 12px;
  padding: 16px;
}
.compare-editor {
  width: 100%;
  min-height: 220px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel-2);
  color: var(--text);
  font:
    500 0.8125rem/1.45 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
  resize: vertical;
}
.compare-editor:focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
.compare-board {
  display: grid;
  gap: 12px;
}
.compare-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.compare-stats span {
  display: inline-flex;
  gap: 6px;
  align-items: baseline;
  min-height: 32px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--panel-2);
  color: var(--muted);
  font-size: 0.8125rem;
}
.compare-stats strong {
  color: var(--text);
}
.compare-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
  margin: 0;
  padding: 0;
  border: 0;
}
.compare-filter legend {
  padding: 0;
  margin-right: 8px;
  font-size: 0.8125rem;
  font-weight: 800;
}
.compare-filter label {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  min-height: 40px;
  font-size: 0.875rem;
}
.compare-empty {
  display: grid;
  gap: 4px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 900px) {
  .compare-panes {
    grid-template-columns: 1fr;
  }
  h1 {
    font-size: 1.6rem;
  }
}
</style>

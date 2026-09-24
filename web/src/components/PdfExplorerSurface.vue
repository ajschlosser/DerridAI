<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as runtime from "../runtime/runtime.js";
import { fullCitation } from "../domain/citations";
import { highlight } from "../domain/recordFormatting";
import AppIcon from "./AppIcon.vue";
import { useI18nStore } from "../stores/i18n";
import { corpusState } from "../state/workspaceState";
import { createPdfExplorerCopy } from "../domain/pdfExplorerCopy";

const i18n = useI18nStore();
const copy = computed(() =>
  createPdfExplorerCopy(
    (key, fallback) => i18n.t(key, fallback),
    (key, fallback, values) =>
      i18n.tf(key, fallback, (values || {}) as Record<string, string | number>),
  ),
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;
const state = runtime.state as unknown as Any;

const mainEl = ref<HTMLElement>();
const fileInputEl = ref<HTMLInputElement>();
const pageInputEl = ref<HTMLInputElement>();
const canvasEl = ref<HTMLCanvasElement>();
const renderStatusEl = ref<HTMLElement>();
const recordSearchEl = ref<HTMLInputElement>();

const loaded = ref(false);
const canRender = ref(false);
const extractReady = ref(false);
const linked = ref<Any[]>([]);
const allRelated = ref<Any[]>([]);
const selectedFile = ref<Any>(null);
const selected = ref<Any>(null);
const hasRecordOptions = ref(false);
const currentOption = ref<{ value: string; label: string } | null>(null);
const pdfTitle = ref("");
const relatedWorks = ref<string[]>([]);
const pdfProvider = ref<Any>(null);
const pageInputValue = ref(1);

const openingPdf = ref(false);
const extractingPage = ref(false);
const extractingAll = ref(false);

const recordSearchInput = ref("");
const recordSearchKey = ref("");
const suggestionsOpen = ref(false);

// state.pdf is the legacy runtime's own (non-reactive) object; a computed() that reads it directly would cache its
// first value forever, since nothing marks it dirty. Mirror the fields the template needs live into plain refs,
// refreshed whenever refresh() runs, and write both the ref and the shared state back together on input.
const relatedSearchQuery = ref("");
const searchQuery = ref("");
const pdfText = ref("");
function setRelatedSearchQuery(value: string) {
  relatedSearchQuery.value = value;
  state.pdf.relatedSearch = value;
}
function setSearchQuery(value: string) {
  searchQuery.value = value;
  state.pdf.search = value;
}

const related = computed(() => {
  const query = relatedSearchQuery.value.trim().toLocaleLowerCase();
  return allRelated.value.filter(
    ({ file, record, pages }: Any) =>
      !query ||
      [
        file.name,
        record.record_id,
        record.work,
        record.document_author,
        record.inline_citation,
        record.full_citation,
        pages.join(" "),
      ].some((value: Any) =>
        String(value || "")
          .toLocaleLowerCase()
          .includes(query),
      ),
  );
});
const relatedShown = computed(() => related.value.slice(0, 80));

const highlightedText = computed(() => {
  const highlighted = highlight(pdfText.value || "", searchQuery.value || "");
  if (highlighted) return highlighted;
  return `<span class="note">${copy.value.emptyExtract}</span>`;
});
const viewerNoteText = computed(
  () =>
    `${canRender.value ? copy.value.renderer : copy.value.fallbackRenderer} · ${copy.value.linkedOnPage(linked.value.length)}`,
);
const linkedCountText = computed(() => copy.value.linkedCount(linked.value.length));
const relatedCountText = computed(() => copy.value.relatedNote(allRelated.value.length));

// AppIcon's "gear" and "copy" paths have each drifted from domain/html.ts's icon() by small path-data differences,
// and that drift is already baked into other components' currently-passing baseline snapshots (SearchView,
// ResearchComposer for "gear"; RecordWorkspaceHeader and others for "copy"). Render the runtime's exact icons here
// instead, so this view's own baseline matches what it always rendered.
const gearIconInner =
  '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-4v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1L7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.1v4H21a1.7 1.7 0 0 0-1.6 1Z"/>';
const copyIconInner =
  '<rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>';
const closeIconInner = '<path d="m6 6 12 12M18 6 6 18"/>';

const suggestions = computed(() =>
  suggestionsOpen.value ? runtime.searchRecordOptions(recordSearchInput.value.trim(), 12) : [],
);

function selectedRelated() {
  return Boolean(
    selectedFile.value && selected.value && runtime.loadedPdfPagesForRecord(selected.value).length,
  );
}

async function refresh() {
  loaded.value = Boolean(state.pdf.file);
  canRender.value = Boolean(state.pdf.doc);
  extractReady.value = Boolean(state.pdf.doc || state.pdf.file);
  linked.value = loaded.value ? runtime.linkedPdfRows(state.pdf.page) : [];
  allRelated.value = loaded.value ? runtime.allLinkedRowsForLoadedPdf() : [];
  selectedFile.value = runtime.activeFile();
  selected.value = runtime.selectedRecord();
  hasRecordOptions.value = state.files.some((file: Any) => file.records.length > 0);
  const currentRecordKey =
    selectedFile.value && selected.value
      ? `${selectedFile.value.id}::${runtime.selectedIndex(selectedFile.value)}`
      : "";
  currentOption.value =
    selectedFile.value && selected.value
      ? {
          value: currentRecordKey,
          label: runtime.recordOptionLabel(
            selectedFile.value,
            selected.value,
            runtime.selectedIndex(selectedFile.value),
          ),
        }
      : null;
  pdfTitle.value = runtime.pdfDisplayTitle();
  relatedWorks.value = [
    ...new Set(allRelated.value.map((item: Any) => String(item.record.work || "")).filter(Boolean)),
  ].sort((a, b) => a.localeCompare(b));
  pdfProvider.value = runtime.defaultProviderProfile();
  pageInputValue.value = state.pdf.page;
  recordSearchInput.value = currentOption.value?.label || "";
  recordSearchKey.value = currentOption.value?.value || "";
  pdfText.value = state.pdf.text || "";
  searchQuery.value = state.pdf.search || "";
  relatedSearchQuery.value = state.pdf.relatedSearch || "";

  await nextTick();
  // The legacy renderer only ran this after the one code path that happened to route through renderView() (which
  // called it, once, on a requestAnimationFrame timed against that render's own async work); every in-page action
  // (rotate, extract, page navigation, linking) called the renderer directly and skipped it, so whether a tall card
  // got its collapse affordance ended up depending on exactly when a completely unrelated action interrupted an
  // in-flight canvas render -- not on anything about the action itself. Checked this against the legacy source
  // before changing it: nothing else reads or depends on that inconsistency, so it is a bug, not a feature. Calling
  // it after every refresh makes the affordance reliably present whenever a card is actually tall enough for it.
  runtime.enhanceCollapsibles(mainEl.value);
  runtime.decorateDisabledControls(mainEl.value);
  if (canRender.value) void renderCanvas();
}

async function renderCanvas() {
  await nextTick();
  if (!canvasEl.value) return;
  await runtime.renderPdfCanvas(state.pdf.page);
}

function openPdfPicker() {
  fileInputEl.value?.click();
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  openingPdf.value = true;
  try {
    if (state.pdf.url) URL.revokeObjectURL(state.pdf.url);
    const buffer = await file.arrayBuffer();
    state.pdf.file = file;
    state.pdf.url = URL.createObjectURL(new Blob([buffer], { type: "application/pdf" }));
    state.pdf.name = file.name;
    state.pdf.title = file.name.replace(/\.pdf$/i, "");
    state.pdf.author = "";
    state.pdf.page = 1;
    state.pdf.rotation = 0;
    state.pdf.text = "";
    state.pdf.search = "";
    state.pdf.relatedSearch = "";
    state.pdf.extractError = "";
    state.pdf.extractionSource = "";
    try {
      const pdfjsLib = await import("pdfjs-dist/legacy/build/pdf.mjs");
      state.pdf.doc = await pdfjsLib.getDocument({ data: new Uint8Array(buffer.slice(0)) }).promise;
      const metadata = await runtime.loadPdfMetadata(state.pdf.doc, file.name);
      state.pdf.title = metadata.title || state.pdf.title;
      state.pdf.author = metadata.author || "";
    } catch (error: Any) {
      console.error("PDF.js initialization failed", error);
      state.pdf.doc = null;
      state.pdf.extractError = copy.value.jsInitFailed(error.message);
    }
    await runtime.persistCurrentPdfAsset();
    runtime.shell();
    await refresh();
  } catch (error: Any) {
    console.error("Could not open PDF", error);
    await runtime.openMessageModal({
      title: copy.value.couldNotOpen,
      message: error.message || String(error),
      tone: "danger",
    });
  } finally {
    openingPdf.value = false;
    if (input) input.value = "";
  }
}

async function setPage(page: Any) {
  const max = state.pdf.doc?.numPages || Math.max(1, page);
  state.pdf.page = Math.max(1, Math.min(max, Number(page) || 1));
  state.pdf.text = "";
  state.pdf.extractError = "";
  state.pdf.extractionSource = "";
  await runtime.persistCurrentPdfAsset();
  runtime.syncUrl({ replace: true });
  await refresh();
}

function goPrev() {
  void setPage(state.pdf.page - 1);
}
function goNext() {
  void setPage(state.pdf.page + 1);
}
function goToPage() {
  void setPage(pageInputEl.value?.value);
}
function onPageInputKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  goToPage();
}

async function rotateLeft() {
  state.pdf.rotation = (Number(state.pdf.rotation || 0) + 270) % 360;
  await runtime.persistCurrentPdfAsset();
  await refresh();
}
async function rotateRight() {
  state.pdf.rotation = (Number(state.pdf.rotation || 0) + 90) % 360;
  await runtime.persistCurrentPdfAsset();
  await refresh();
}

async function extractPage() {
  const pageToExtract = Number(pageInputEl.value?.value || state.pdf.page);
  state.pdf.page = Math.max(1, Math.min(state.pdf.doc?.numPages || pageToExtract, pageToExtract));
  extractingPage.value = true;
  try {
    const result = await runtime.extractPdfPageSmart(state.pdf.page);
    state.pdf.text = result.text;
    state.pdf.extractionSource = result.source;
    state.pdf.extractError = result.warning || "";
  } catch (error: Any) {
    state.pdf.extractError = error.message;
  }
  extractingPage.value = false;
  await refresh();
}

async function extractAll() {
  extractingAll.value = true;
  try {
    const result = await runtime.extractPdfAllSmart();
    state.pdf.text = result.text;
    state.pdf.extractionSource = result.source;
    state.pdf.extractError = result.warning || "";
  } catch (error: Any) {
    state.pdf.extractError = error.message;
  }
  extractingAll.value = false;
  await refresh();
}

function openLlmClean() {
  runtime.cleanPdfPageWithLlm();
}
function openLlmDraft() {
  runtime.draftPdfPageWithLlm();
}
function openLlmLink() {
  runtime.linkPdfPageWithLlm();
}
function openProviders() {
  runtime.navigateTo("providers");
}
function openCorpusBuilder() {
  window.dispatchEvent(new CustomEvent("derridai:pdf-builder"));
}
function returnToSelectedRecord() {
  if (!selectedFile.value) return;
  runtime.navigateTo("record", {
    fileId: selectedFile.value.id,
    index: runtime.selectedIndex(selectedFile.value),
  });
}
function openLinkedRecord(fileId: string, index: number) {
  runtime.navigateTo("record", { fileId, index });
}
function unlinkRecord(fileId: string, index: number) {
  const file = state.files.find((item: Any) => item.id === fileId);
  if (!file) return;
  runtime.unlinkPdfLink(
    file,
    index,
    { pdf_file: state.pdf.name, pdf_page: state.pdf.page },
    { stayInPdf: true },
  );
}
function evidenceKey(fileId: string, index: number) {
  const file = state.files.find((item: Any) => item.id === fileId);
  return file ? runtime.workspaceEvidenceSelectionKey(file, index) : "";
}

function onRecordSearchFocus() {
  suggestionsOpen.value = true;
}
function onRecordSearchInput(event: Event) {
  recordSearchInput.value = (event.target as HTMLInputElement).value;
  recordSearchKey.value = "";
  suggestionsOpen.value = true;
}
function onRecordSearchKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") suggestionsOpen.value = false;
}
function chooseSuggestion(option: { value: string; label: string }) {
  recordSearchKey.value = option.value;
  recordSearchInput.value = option.label;
  suggestionsOpen.value = false;
}
function onDocumentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  if (!target?.closest(".autocomplete")) suggestionsOpen.value = false;
}

function linkCurrentPdf() {
  let key = recordSearchKey.value;
  if (!key) {
    const exact = runtime
      .searchRecordOptions(recordSearchInput.value, 24)
      .find((option: Any) => option.label === recordSearchInput.value);
    key = exact?.value || "";
  }
  const item = runtime.lookupRecord(key);
  if (item) runtime.linkPdfPage(item.file, item.index, state.pdf.page);
  else runtime.toast(copy.value.chooseAutocomplete);
}

// Some runtime code (unlinking a record, applying LLM cleanup results) still asks the PDF Explorer to refresh this
// way; it used to call the legacy renderer directly, and now dispatches this event instead of reaching into a Vue
// component -- the same bridge pattern already used for the dashboard.
function onPdfExplorerRefreshRequested() {
  void refresh();
}

watch(
  () => [corpusState.version, corpusState.activeFileId],
  () => void refresh(),
  { flush: "post" },
);

onMounted(async () => {
  runtime.syncUrl({ replace: true });
  await refresh();
  document.addEventListener("click", onDocumentClick);
  window.addEventListener("derridai:pdf-explorer-refresh", onPdfExplorerRefreshRequested);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  window.removeEventListener("derridai:pdf-explorer-refresh", onPdfExplorerRefreshRequested);
});
</script>

<template>
  <main id="main" class="runtime-surface" aria-live="polite" ref="mainEl">
    <section class="card pdf-document-header">
      <input
        id="pdfInput"
        ref="fileInputEl"
        type="file"
        accept="application/pdf"
        hidden
        @change="onFileChange"
      />
      <div class="pdf-document-primary">
        <button class="btn primary" id="openPdf" @click="openPdfPicker">
          <template v-if="openingPdf"
            ><span class="spinner small-spinner"></span>{{ copy.opening }}</template
          ><template v-else
            ><AppIcon name="pdf" />{{ loaded ? copy.openAnother : copy.openPdf }}</template
          >
        </button>
        <div class="pdf-document-title">
          <template v-if="loaded">
            <span>{{ copy.document }}</span>
            <h2>{{ pdfTitle }}</h2>
            <p>
              {{ state.pdf.name }}{{ state.pdf.author ? ` · ${state.pdf.author}` : ""
              }}{{ state.pdf.doc ? ` · ${copy.pagesCount(state.pdf.doc.numPages)}` : "" }}
            </p>
          </template>
          <template v-else>
            <span>{{ copy.explorer }}</span>
            <h2>{{ copy.openSource }}</h2>
            <p v-text="copy.openHelp"></p>
          </template>
        </div>
        <div v-if="loaded" class="pdf-document-status">
          <span
            ><b>{{ relatedWorks.length }}</b> {{ copy.linkedWorks }}</span
          >
          <span
            ><b>{{ allRelated.length }}</b> {{ copy.linkedRecords }}</span
          >
          <span
            ><b>{{ linked.length }}</b> {{ copy.onThisPage }}</span
          >
        </div>
      </div>
      <template v-if="loaded">
        <div class="pdf-command-row">
          <div class="pdf-page-nav">
            <button
              class="btn small icon-only"
              id="pdfPrev"
              :disabled="state.pdf.page <= 1"
              @click="goPrev"
              v-text="'←'"
            ></button>
            <label
              ><span>{{ copy.page }}</span
              ><input
                class="control pdf-page-input"
                id="pdfPageInput"
                ref="pageInputEl"
                type="number"
                min="1"
                :max="state.pdf.doc?.numPages || 999999"
                :value.attr="pageInputValue"
                @keydown="onPageInputKeydown"
            /></label>
            <span class="pdf-page-total">/ {{ state.pdf.doc?.numPages || "?" }}</span>
            <button class="btn small" id="pdfGo" @click="goToPage">{{ copy.go }}</button>
            <button
              class="btn small icon-only"
              id="pdfNext"
              :disabled="state.pdf.doc && state.pdf.page >= state.pdf.doc.numPages"
              @click="goNext"
              v-text="'→'"
            ></button>
          </div>
          <div class="pdf-command-divider"></div>
          <div class="pdf-view-actions">
            <button
              class="btn small icon-only"
              id="pdfRotateLeft"
              :title="copy.rotateLeft"
              @click="rotateLeft"
              v-text="'↶'"
            ></button>
            <button
              class="btn small icon-only"
              id="pdfRotateRight"
              :title="copy.rotateRight"
              @click="rotateRight"
              v-text="'↷'"
            ></button>
            <span class="note">{{
              state.pdf.rotation ? copy.rotationAmount(state.pdf.rotation) : copy.upright
            }}</span>
          </div>
          <div class="pdf-command-divider"></div>
          <button
            class="btn small"
            id="extractPage"
            :disabled="!extractReady"
            @click="extractPage"
            v-text="extractingPage ? copy.extractingPage(state.pdf.page) : copy.extractPage"
          ></button>
          <details class="pdf-toolbar-menu">
            <summary class="btn small">{{ copy.moreTextTools }}</summary>
            <div class="pdf-toolbar-menu-popover">
              <button
                class="btn small"
                id="extractAll"
                :disabled="!extractReady"
                @click="extractAll"
                v-text="extractingAll ? copy.extracting : copy.extractAll"
              ></button>
            </div>
          </details>
          <details class="pdf-toolbar-menu llm-menu">
            <summary class="btn small soft"><AppIcon name="spark" />{{ copy.llmTools }}</summary>
            <div class="pdf-toolbar-menu-popover">
              <div class="pdf-menu-context">
                <b>{{ runtime.providerDisplayName(pdfProvider) }}</b>
                <span>{{ copy.llmToolsHelp }}</span>
              </div>
              <button
                class="btn small"
                id="pdfLlmClean"
                :disabled="!extractReady"
                @click="openLlmClean"
                v-text="copy.cleanPage"
              ></button>
              <button
                class="btn small"
                id="pdfLlmDraft"
                :disabled="!extractReady"
                @click="openLlmDraft"
                v-text="copy.draftRecord"
              ></button>
              <button
                class="btn small"
                id="pdfLlmLink"
                :disabled="!state.files.length"
                @click="openLlmLink"
                v-text="copy.matchLink"
              ></button>
              <button class="btn small" id="pdfProviders" @click="openProviders">
                <!-- AppIcon's own "gear" path has drifted from this one by a coordinate, and that drift is already
                baked into two other passing baseline snapshots elsewhere; render the runtime's exact icon here
                instead of introducing a wrapping element that v-html on a span would add. -->
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                  v-html="gearIconInner"
                ></svg
                >{{ copy.manageProviders }}</button>
            </div>
          </details>
          <button class="btn small primary" id="pdfCorpusBuilder" @click="openCorpusBuilder"
            ><AppIcon name="spark" />{{ copy.buildRecordSet }}</button>
        </div>
        <div class="pdf-context-row">
          <div class="pdf-context-pill">
            <span>{{ copy.source }}</span><b>p. {{ state.pdf.page }}</b>
          </div>
          <div class="pdf-context-pill">
            <span>{{ copy.works }}</span>
            <b
              >{{ relatedWorks.slice(0, 2).join(" · ") || copy.noneLinked
              }}{{ relatedWorks.length > 2 ? ` +${relatedWorks.length - 2}` : "" }}</b
            >
          </div>
          <div class="pdf-context-pill">
            <span>{{ copy.currentPageRecords }}</span><b>{{ linked.length }}</b>
          </div>
          <button
            v-if="selectedRelated()"
            class="btn soft"
            id="returnToSelectedRecord"
            @click="returnToSelectedRecord"
          >
            <AppIcon name="record" />{{ copy.backTo(selected?.record_id || copy.recordFallback) }}
          </button>
        </div>
      </template>
    </section>
    <section v-if="loaded" class="pdfgrid pdfgrid-v2">
      <article class="card pdf-viewer-card">
        <div class="cardhead pdf-viewer-head">
          <div>
            <b>{{ copy.page }} {{ state.pdf.page }}</b>
            <div class="note" v-text="viewerNoteText"></div>
          </div>
          <span class="pdf-view-badge">{{
            state.pdf.rotation ? copy.rotation(state.pdf.rotation) : copy.fitWidth
          }}</span>
        </div>
        <div v-if="canRender" class="pdf-canvas-wrap">
          <canvas id="pdfCanvas" ref="canvasEl"></canvas>
          <div class="pdf-render-status" id="pdfRenderStatus" ref="renderStatusEl"></div>
        </div>
        <iframe
          v-else
          class="pdf-frame"
          id="pdfFrame"
          :title="pdfTitle"
          :src="`${state.pdf.url}#page=${state.pdf.page}`"
        ></iframe>
      </article>
      <aside class="pdf-side-stack">
        <article class="card pdf-text-card">
          <div class="cardhead">
            <div>
              <b>{{ copy.pageText }}</b>
              <div class="note">
                {{
                  state.pdf.extractionSource
                    ? copy.sourceLabel(state.pdf.extractionSource)
                    : copy.extractThenClean
                }}
              </div>
            </div>
            <div class="search">
              <input
                id="pdfSearch"
                :value.attr="searchQuery"
                :placeholder="copy.searchPage"
                @input="setSearchQuery(($event.target as HTMLInputElement).value)"
              />
            </div>
          </div>
          <div v-if="state.pdf.extractError" class="info warn" style="margin: 14px">
            {{ state.pdf.extractError }}
          </div>
          <div class="pdftext" v-html="highlightedText"></div>
        </article>
        <article class="card panel pdf-current-links">
          <div class="toolbar compact-toolbar">
            <div>
              <b>{{ copy.recordsOnPage(state.pdf.page) }}</b>
              <div class="note" v-text="linkedCountText"></div>
            </div>
          </div>
          <div class="pdf-link-controls">
            <div class="autocomplete">
              <input
                class="control"
                id="pdfRecordSearch"
                ref="recordSearchEl"
                autocomplete="off"
                :placeholder="copy.searchRecord"
                :value.attr="recordSearchInput"
                @focus="onRecordSearchFocus"
                @input="onRecordSearchInput"
                @keydown="onRecordSearchKeydown"
              />
              <input type="hidden" id="pdfRecordKey" :value.attr="recordSearchKey" />
              <div
                class="autocomplete-list"
                id="pdfRecordSuggestions"
                :class="{ hidden: !suggestionsOpen }"
              >
                <template v-if="suggestionsOpen">
                  <template v-if="suggestions.length">
                    <button
                      v-for="option in suggestions"
                      :key="option.value"
                      type="button"
                      class="autocomplete-option"
                      :data-record-key="option.value"
                      @click="chooseSuggestion(option)"
                    >
                      <b>{{ option.label.split(" · ")[1] || option.label }}</b>
                      <span>{{ option.label }}</span>
                    </button>
                  </template>
                  <div v-else class="autocomplete-empty">{{ copy.noMatching }}</div>
                </template>
              </div>
            </div>
            <button
              class="btn"
              id="linkCurrentPdf"
              :disabled="!hasRecordOptions"
              @click="linkCurrentPdf"
            >
              <AppIcon name="plus" />{{ copy.linkPage(state.pdf.page) }}
            </button>
          </div>
          <div class="pdf-linked-list">
            <template v-if="linked.length">
              <div
                v-for="({ file, record, index }, i) in linked"
                :key="i"
                class="linked-record-row"
              >
                <button
                  class="linked-record"
                  :data-linked-file="file.id"
                  :data-linked-index="index"
                  @click="openLinkedRecord(file.id, index)"
                >
                  <b>{{ record.record_id || copy.recordN(index + 1) }}</b>
                  <span
                    >{{ record.work || file.name }} ·
                    {{ record.inline_citation || runtime.pages(record) }}</span
                  >
                </button>
                <div class="tools">
                  <button class="btn small" :data-copy-row-key="runtime.reviewKey(file, index)">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      aria-hidden="true"
                      v-html="copyIconInner"
                    ></svg
                    >{{ copy.copy }}</button
                  >
                  <button
                    class="btn small"
                    :data-cite-row-key="runtime.reviewKey(file, index)"
                    data-cite-kind="inline"
                    :title="i18n.t('ui.copy_inline')"
                    v-text="copy.inline"
                  ></button>
                  <button
                    class="btn small"
                    :data-cite-row-key="runtime.reviewKey(file, index)"
                    data-cite-kind="full"
                    :title="i18n.t('ui.copy_full')"
                    v-text="copy.full"
                  ></button>
                  <button
                    class="btn small"
                    :class="{ soft: runtime.evidenceIsSelected(evidenceKey(file.id, index)) }"
                    :data-toggle-workspace-evidence="runtime.reviewKey(file, index)"
                    :title="
                      runtime.evidenceIsSelected(evidenceKey(file.id, index))
                        ? i18n.t('ui.remove_evidence')
                        : i18n.t('ui.add_evidence')
                    "
                  >
                    <AppIcon
                      :name="
                        runtime.evidenceIsSelected(evidenceKey(file.id, index)) ? 'check' : 'plus'
                      "
                      />{{ copy.evidence }}</button>
                  <button
                    class="btn small"
                    :data-linked-open-file="file.id"
                    :data-linked-open-index="index"
                    @click="openLinkedRecord(file.id, index)"
                    ><AppIcon name="record" />{{ copy.openRecord }}</button
                  >
                  <button
                    class="btn small danger unlink-pdf-link"
                    :data-unlink-file="file.id"
                    :data-unlink-index="index"
                    :title="copy.unlinkTitle"
                    @click="unlinkRecord(file.id, index)"
                    ><svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      aria-hidden="true"
                      v-html="closeIconInner"
                    ></svg
                    >{{ copy.unlink }}</button>
                </div>
              </div>
            </template>
            <div v-else class="note">{{ copy.noLinkedYet }}</div>
          </div>
        </article>
        <article class="card panel pdf-related-records">
          <div class="toolbar compact-toolbar">
            <div>
              <b>{{ copy.recordsAnywhere }}</b>
              <div class="note" v-text="relatedCountText"></div>
            </div>
          </div>
          <div class="search pdf-related-search">
            <input
              id="pdfRelatedSearch"
              :value.attr="relatedSearchQuery"
              :placeholder="copy.filterLinked"
              @input="setRelatedSearchQuery(($event.target as HTMLInputElement).value)"
            />
          </div>
          <div class="pdf-related-list">
            <template v-if="relatedShown.length">
              <div
                v-for="({ file, record, index, pages: recordPages }, i) in relatedShown"
                :key="i"
                class="pdf-related-row"
              >
                <button
                  class="pdf-related-record"
                  :data-related-record-file="file.id"
                  :data-related-record-index="index"
                  @click="openLinkedRecord(file.id, index)"
                >
                  <b>{{ record.record_id || copy.recordN(index + 1) }}</b>
                  <span>{{ record.work || file.name }}</span>
                  <small>{{ fullCitation(record) || file.name }}</small>
                </button>
                <div class="pdf-related-pages">
                  <button
                    class="copy-record-mini"
                    :data-copy-row-key="runtime.reviewKey(file, index)"
                    :title="copy.copyEntire"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      aria-hidden="true"
                      v-html="copyIconInner"
                    ></svg
                  ></button>
                  <button
                    class="copy-record-mini"
                    :data-cite-row-key="runtime.reviewKey(file, index)"
                    data-cite-kind="inline"
                    :title="i18n.t('ui.copy_inline')"
                    v-text="'I'"
                  ></button>
                  <button
                    class="copy-record-mini"
                    :data-cite-row-key="runtime.reviewKey(file, index)"
                    data-cite-kind="full"
                    :title="i18n.t('ui.copy_full')"
                    v-text="'F'"
                  ></button>
                  <button
                    class="copy-record-mini"
                    :class="{ selected: runtime.evidenceIsSelected(evidenceKey(file.id, index)) }"
                    :data-toggle-workspace-evidence="runtime.reviewKey(file, index)"
                    :title="
                      runtime.evidenceIsSelected(evidenceKey(file.id, index))
                        ? i18n.t('ui.remove_evidence')
                        : i18n.t('ui.add_evidence')
                    "
                    v-text="runtime.evidenceIsSelected(evidenceKey(file.id, index)) ? '✓' : '+'"
                  ></button>
                  <button
                    v-for="page in recordPages"
                    :key="page"
                    class="pdf-page-chip"
                    :class="{ active: Number(page) === Number(state.pdf.page) }"
                    :data-related-page="page"
                    :title="copy.openPdfPage(page)"
                    @click="setPage(page)"
                    v-text="`p. ${page}`"
                  ></button>
                </div>
              </div>
            </template>
            <div v-else class="note">{{ copy.noFilterMatch }}</div>
          </div>
          <div v-if="related.length > 80" class="note" style="padding-top: 8px">
            {{ copy.showingFirst(80, related.length) }}
          </div>
        </article>
      </aside>
    </section>
    <section v-else class="empty">
      <div class="drop">
        <div class="drop-icon"><AppIcon name="pdf" /></div>
        <h1>{{ copy.explorer }}</h1>
        <p v-text="copy.emptyHelp"></p>
        <button class="btn primary" id="openPdf2" @click="openPdfPicker"
          ><AppIcon name="pdf" />{{ copy.choosePdf }}</button
        >
      </div>
    </section>
  </main>
</template>

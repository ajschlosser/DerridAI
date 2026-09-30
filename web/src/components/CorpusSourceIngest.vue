<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { GutenbergHit, PdfAsset, WikisourceHit, GutenbergStatus } from "../api/corpus";
import type { SourceLanguagePrompt } from "../features/corpus-builder/composables/useCorpusSourceConfiguration";

import { hasPages, sourceMediaCapabilities } from "../domain/sourceMedia";
import { languageName, sortLanguageCodes } from "../domain/languages";
import AppIcon from "./AppIcon.vue";
import CorpusLibrarySearch from "./corpus-builder/CorpusLibrarySearch.vue";
import CorpusImportShell from "./corpus-builder/CorpusImportShell.vue";
import CorpusCaptureDialog from "./capture/CorpusCaptureDialog.vue";
import SourceTable from "./sources/SourceTable.vue";
import SourceInspector from "./sources/SourceInspector.vue";
import UiButton from "./ui/UiButton.vue";
import UiCombobox from "./ui/UiCombobox.vue";
import UiDialog from "./ui/UiDialog.vue";
import UiTooltip from "./ui/UiTooltip.vue";
import type { CorpusCapture } from "../api/corpus";
const formats: Record<string, string> = {
  pdf: ".pdf",
  text: ".txt,.text,.md,.html,.htm",
  docx: ".docx",
  rtf: ".rtf",
  image: ".png,.jpg,.jpeg",
  audio: ".mp3,.wav,.m4a,.ogg,.flac,.webm,.mp4,.mpeg,.mpga,.aac",
};

const props = withDefaults(
  defineProps<{
    assets?: PdfAsset[];
    assetId?: string;
    illegibility?: number;
    detectPageNumbers?: boolean;
    llmPageDetection?: boolean;
    sourceUrl?: string;
    gutenbergQuery?: string;
    hits?: GutenbergHit[];
    wikisourceHits?: WikisourceHit[];
    wikisourceLanguage?: string;
    librarySearched?: { gutenberg: string; wikisource: string };
    libraryError?: string;
    libraryImporting?: string;
    libraryImported?: number;
    gutenbergStatus?: GutenbergStatus | null;
    selectedAsset?: PdfAsset | null;
    disabled?: boolean;
    sourceSelectionDisabled?: boolean;
    busy?: string;
    /** Source ids handed over from the Sources page or a capture (`/pdf?sources=…`). */
    queuedSourceIds?: string[];
    languagePrompt?: SourceLanguagePrompt | null;
  }>(),
  {
    assets: () => [],
    assetId: "",
    illegibility: 0,
    detectPageNumbers: true,
    llmPageDetection: true,
    sourceUrl: "",
    gutenbergQuery: "",
    hits: () => [],
    wikisourceHits: () => [],
    wikisourceLanguage: "en",
    librarySearched: () => ({ gutenberg: "", wikisource: "" }),
    libraryError: "",
    libraryImporting: "",
    libraryImported: 0,
    gutenbergStatus: null,
    selectedAsset: null,
    disabled: false,
    sourceSelectionDisabled: false,
    busy: "",
    queuedSourceIds: () => [],
    languagePrompt: null,
  },
);

const emit = defineEmits<{
  "update:assetId": [string];
  "update:illegibility": [number];
  "update:detectPageNumbers": [boolean];
  "update:llmPageDetection": [boolean];
  "update:sourceUrl": [string];
  "update:gutenbergQuery": [string];
  "update:wikisourceLanguage": [string];
  useCurrent: [];
  file: [File];
  loadUrl: [];
  searchGutenberg: [];
  searchWikisource: [];
  refreshGutenbergStatus: [];
  refreshGutenbergCatalogue: [];
  updateGutenbergArchive: [action: "start" | "pause" | "resume" | "refetch"];
  importGutenberg: [number];
  importWikisource: [string];
  deleteAsset: [string];
  continue: [];
  /** Captured sources to offer in the source table (never starts a build). */
  queueSources: [ids: string[]];
  /** A capture registered new sources; the asset list should be reloaded. */
  sourcesChanged: [];
  viewCaptureSources: [captureId: string];
  "save-language": [language: string | null];
}>();

const i18n = useI18nStore();
const uploadInput = ref<HTMLInputElement | null>(null);
const searchOpen = ref(false);
const importShellOpen = ref(false);
const importShellMode = ref<"library" | "author">("library");
/** The source whose inline "delete?" confirmation is showing. */
const confirmingDelete = ref("");
const languageDraft = ref("");
const languageOptions = computed(() =>
  sortLanguageCodes(
    ["en", "fr", "de", "es", "it", "pt", "nl", "la", "grc", "ar", "he", "ru", "ja", "zh"],
    i18n.locale,
  ),
);
watch(
  () => props.languagePrompt,
  (prompt) => {
    languageDraft.value = prompt?.suggestion || "";
  },
  { immediate: true },
);
function confirmDelete(assetId: string) {
  confirmingDelete.value = "";
  emit("deleteAsset", assetId);
}

const sourceSetupDisabled = computed(() => props.disabled || props.sourceSelectionDisabled);
const selectedMediaKind = computed(() => props.selectedAsset?.media_kind || "");
const ocrAvailable = computed(
  () => Boolean(selectedMediaKind.value) && sourceMediaCapabilities(selectedMediaKind.value).imageRegions,
);

const ocrStrategy = computed(() => {
  if (props.illegibility >= 99.9) return "always";
  if (props.illegibility > 0) return "difficult";
  return "embedded";
});

function mediaKind(kind?: string) {
  if (!kind) return "";
  return i18n.t(`pdf_corpus.media_kind.${kind}`, kind);
}

function unset() {
  return i18n.t("pdf_corpus.metadata_unset");
}

function formatDate(value?: string | null) {
  if (!value) return unset();
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function pageDetectionText(detection: NonNullable<PdfAsset["page_number_detection"]>) {
  if (detection.status === "detected") {
    return i18n.tf("pdf_corpus.source_page_detected", {
      count: detection.marker_count ?? 0,
      first: detection.first ?? "?",
      last: detection.last ?? "?",
      pattern: i18n.t(
        `pdf_corpus.page_pattern_${detection.pattern || "bare"}`,
        detection.pattern || "",
      ),
      confidence: Math.round((detection.confidence ?? 0) * 100),
    });
  }
  return i18n.t(
    detection.status === "disabled"
      ? "pdf_corpus.source_page_detect_off"
      : "pdf_corpus.source_page_not_found",
  );
}

function onOcrStrategy(strategy: string) {
  emit("update:illegibility", strategy === "always" ? 100 : strategy === "difficult" ? 50 : 0);
}

function onFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) emit("file", file);
  input.value = "";
}

function openSearch() {
  importShellMode.value = "library";
  importShellOpen.value = true;
}
function openAuthorCapture() {
  importShellMode.value = "author";
  importShellOpen.value = true;
}
function selectImportMode(mode: "library" | "author") {
  importShellOpen.value = false;
  // Close the chooser before mounting the selected dialog so focus restoration
  // cannot race the next modal's focus setup.
  void nextTick(() => {
    if (mode === "library") searchOpen.value = true;
    else captureOpen.value = true;
  });
}

// --- Drop zone -------------------------------------------------------------
const dragging = ref(false);
let dragDepth = 0;
function onDragEnter() {
  if (sourceSetupDisabled.value) return;
  dragDepth += 1;
  dragging.value = true;
}
function onDragLeave() {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) dragging.value = false;
}
function onDrop(event: DragEvent) {
  dragDepth = 0;
  dragging.value = false;
  if (sourceSetupDisabled.value) return;
  const transfer = event.dataTransfer;
  const file = transfer?.files?.[0];
  if (file) {
    emit("file", file);
    return;
  }
  // A dragged link becomes a URL import.
  const dropped = (transfer?.getData("text/uri-list") || transfer?.getData("text/plain") || "")
    .split("\n")[0]
    .trim();
  if (/^https?:\/\//i.test(dropped)) {
    emit("update:sourceUrl", dropped);
    void nextTick(() => emit("loadUrl"));
  }
}

// --- Web address -----------------------------------------------------------
const urlOpen = ref(Boolean(props.sourceUrl.trim()));
// A pasted or dropped link opens the address panel so it can be checked and loaded.
watch(
  () => props.sourceUrl,
  (value) => {
    if (value.trim()) urlOpen.value = true;
  },
);
const urlKind = computed<"" | "wikisource" | "gutenberg" | "web">(() => {
  const value = props.sourceUrl.trim();
  if (!/^https?:\/\/\S+$/i.test(value)) return "";
  if (/(^|\.)wikisource\.org\//i.test(value.replace(/^https?:\/\//i, ""))) return "wikisource";
  if (/(^|\.)gutenberg\.org\//i.test(value.replace(/^https?:\/\//i, ""))) return "gutenberg";
  return "web";
});
async function toggleUrl() {
  urlOpen.value = !urlOpen.value;
  if (urlOpen.value) {
    await nextTick();
    document.getElementById("pdf-corpus-source-url")?.focus();
  }
}

// --- Saved sources ---------------------------------------------------------
/** Reload the compact table whenever the parent's asset list changes (upload, import, delete). */
const assetsKey = computed(() => props.assets.map((asset) => asset.asset_id).join(","));
const inspectedSource = ref("");
function deleteName(assetId: string) {
  return props.assets.find((asset) => asset.asset_id === assetId)?.filename || assetId;
}

const KIND_MARKS: Record<string, string> = {
  pdf: "PDF",
  text: "TXT",
  docx: "DOCX",
  rtf: "RTF",
  image: "IMG",
  audio: "AUD",
};
function kindMark(asset: { media_kind?: string; filename: string }) {
  if (asset.media_kind && KIND_MARKS[asset.media_kind]) return KIND_MARKS[asset.media_kind];
  const extension = asset.filename.split(".").pop() || "";
  return extension.length <= 4 ? extension.toUpperCase() : "FILE";
}

// --- Corpus Capture ----------------------------------------------------------
const captureOpen = ref(false);
function onCaptureChanged(capture: CorpusCapture) {
  if (!capture.active_job && ["complete", "partial"].includes(capture.status))
    emit("sourcesChanged");
}
function useCaptured(ids: string[]) {
  captureOpen.value = false;
  emit("queueSources", ids);
}
const formatChips = ["PDF", "DOCX", "RTF", "TXT · MD · HTML", "PNG · JPG", "Audio"];

// --- Current source --------------------------------------------------------
const copied = ref(false);
let copiedTimer: number | null = null;
async function copyHash() {
  if (!props.selectedAsset) return;
  try {
    await navigator.clipboard.writeText(props.selectedAsset.sha256);
    copied.value = true;
    if (copiedTimer !== null) window.clearTimeout(copiedTimer);
    copiedTimer = window.setTimeout(() => (copied.value = false), 1600);
  } catch {
    copied.value = false;
  }
}
onBeforeUnmount(() => {
  if (copiedTimer !== null) window.clearTimeout(copiedTimer);
});
</script>

<template>
  <div class="source-ingest" :aria-busy="busy ? 'true' : undefined">
    <div class="source-stage">
      <section class="add-source" aria-labelledby="source-add-title">
        <h4 id="source-add-title" class="stage-title">
          <span class="stage-step" aria-hidden="true">1</span>
          {{ i18n.t("pdf_corpus.source_stage_add") }}
        </h4>

        <fieldset v-if="ocrAvailable" class="ocr-choice" :disabled="sourceSetupDisabled">
          <legend>{{ i18n.t("pdf_corpus.source_illegibility") }}</legend>
          <small id="source-illegibility-help">{{
            i18n.t("pdf_corpus.source_illegibility_help")
          }}</small>
          <div class="ocr-options">
            <label
              v-for="option in [
                ['embedded', 'source_ocr_embedded', 'source_ocr_embedded_help'],
                ['difficult', 'source_ocr_difficult', 'source_ocr_difficult_help'],
                ['always', 'source_ocr_always', 'source_ocr_always_help'],
              ]"
              :key="option[0]"
              :class="{ 'is-selected': ocrStrategy === option[0] }"
            >
              <input
                name="source-ocr-strategy"
                type="radio"
                :value="option[0]"
                :checked="ocrStrategy === option[0]"
                @change="onOcrStrategy(option[0])"
              />
              <span class="ocr-option-title">{{ i18n.t(`pdf_corpus.${option[1]}`) }}</span>
              <span class="ocr-option-help">{{ i18n.t(`pdf_corpus.${option[2]}`) }}</span>
            </label>
          </div>
        </fieldset>

        <button
          type="button"
          class="dropzone source-choose"
          :class="{ 'is-over': dragging, 'is-busy': busy === 'upload' }"
          :disabled="sourceSetupDisabled"
          :aria-describedby="'source-formats source-auto-detect'"
          @click="uploadInput?.click()"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
        >
          <span class="dropzone-icon" aria-hidden="true"><AppIcon name="upload" /></span>
          <span class="dropzone-title">{{
            busy === "upload"
              ? i18n.t("pdf_corpus.source_drop_busy")
              : dragging
                ? i18n.t("pdf_corpus.source_drop_release")
                : i18n.t("pdf_corpus.source_drop_title")
          }}</span>
          <span class="dropzone-sub">{{ i18n.t("pdf_corpus.choose_pdf") }}</span>
          <span v-if="busy === 'upload'" class="dropzone-progress" aria-hidden="true"></span>
        </button>
        <p v-if="busy === 'upload'" class="source-loading" role="status">
          <span class="spinner" aria-hidden="true"></span>
          <span>{{ i18n.t("pdf_corpus.source_loading_status") }}</span>
        </p>
        <input
          ref="uploadInput"
          :disabled="sourceSetupDisabled"
          class="sr-only"
          tabindex="-1"
          type="file"
          :accept="Object.values(formats).join(',')"
          :aria-label="i18n.t('pdf_corpus.choose_pdf')"
          @change="onFile"
        />
        <ul
          id="source-formats"
          class="format-chips"
          :aria-label="i18n.t('pdf_corpus.source_formats_label')"
        >
          <li v-for="chip in formatChips" :key="chip">{{ chip }}</li>
        </ul>
        <p id="source-auto-detect" class="auto-detect-note">
          {{ i18n.t("pdf_corpus.source_auto_detect") }}
        </p>

        <div class="source-paths">
          <button
            type="button"
            class="path-card path-libraries"
            :disabled="disabled"
            @click="openSearch"
          >
            <span class="path-icon" aria-hidden="true"><AppIcon name="books" /></span>
            <span class="path-copy">
              <strong>{{ i18n.t("pdf_corpus.search_library", "Search digital libraries") }}</strong>
              <small>{{ i18n.t("pdf_corpus.source_path_libraries_help") }}</small>
            </span>
          </button>
          <button
            type="button"
            class="path-card path-capture"
            :disabled="disabled"
            @click="openAuthorCapture"
          >
            <span class="path-icon" aria-hidden="true"><AppIcon name="users" /></span>
            <span class="path-copy">
              <strong>{{ i18n.t("capture.path_title") }}</strong>
              <small>{{ i18n.t("capture.path_help") }}</small>
            </span>
          </button>
          <button
            type="button"
            class="path-card path-web"
            :aria-expanded="urlOpen"
            aria-controls="source-url-panel"
            :disabled="disabled"
            @click="toggleUrl"
          >
            <span class="path-icon" aria-hidden="true"><AppIcon name="language" /></span>
            <span class="path-copy">
              <strong>{{ i18n.t("pdf_corpus.source_path_web") }}</strong>
              <small>{{ i18n.t("pdf_corpus.source_path_web_help") }}</small>
            </span>
          </button>
          <button
            v-if="selectedAsset?.media_kind === 'pdf'"
            type="button"
            class="path-card path-explorer"
            :disabled="sourceSetupDisabled"
            @click="emit('useCurrent')"
          >
            <span class="path-icon" aria-hidden="true"><AppIcon name="pdf" /></span>
            <span class="path-copy">
              <strong>{{ i18n.t("pdf_corpus.use_current_pdf") }}</strong>
              <small>{{ i18n.t("pdf_corpus.source_path_explorer_help") }}</small>
            </span>
          </button>
        </div>

        <form
          v-show="urlOpen"
          id="source-url-panel"
          class="url-source"
          @submit.prevent="emit('loadUrl')"
        >
          <label for="pdf-corpus-source-url">
            <span>{{ i18n.t("pdf_corpus.source_url") }}</span>
            <input
              id="pdf-corpus-source-url"
              class="control"
              type="url"
              inputmode="url"
              :value="sourceUrl"
              :placeholder="i18n.t('pdf_corpus.url_placeholder')"
              :disabled="disabled"
              @input="emit('update:sourceUrl', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <button type="submit" class="btn primary" :disabled="disabled || !sourceUrl.trim()">
            {{ i18n.t("pdf_corpus.load_url") }}
          </button>
          <p v-if="urlKind" class="url-detect" :data-kind="urlKind" role="status">
            <AppIcon name="check" />
            {{ i18n.t(`pdf_corpus.source_url_kind_${urlKind}`) }}
          </p>
        </form>
      </section>

      <section class="current-source" aria-labelledby="source-current-title">
        <h4 id="source-current-title" class="stage-title">
          <span class="stage-step" aria-hidden="true">2</span>
          {{ i18n.t("pdf_corpus.source_current_title") }}
        </h4>
        <article v-if="selectedAsset" class="source-card">
          <header class="source-card-head">
            <span class="kind-mark" aria-hidden="true">{{ kindMark(selectedAsset) }}</span>
            <div>
              <h5>{{ selectedAsset.filename }}</h5>
              <p>
                <span class="ready-chip"
                  ><AppIcon name="check" />{{ i18n.t("pdf_corpus.source_ready") }}</span
                >
                <span v-if="selectedAsset.media_kind">{{
                  mediaKind(selectedAsset.media_kind)
                }}</span>
              </p>
            </div>
          </header>
          <dl class="stat-tiles">
            <div v-if="hasPages(selectedAsset.media_kind)">
              <dt>{{ i18n.t("pdf_corpus.source_stat_pages") }}</dt>
              <dd>{{ selectedAsset.page_count }}</dd>
            </div>
            <div>
              <dt class="source-fact-label">
                {{ i18n.t("pdf_corpus.source_stat_units") }}
                <UiTooltip :text="i18n.t('pdf_corpus.source_units_help')" placement="bottom" />
              </dt>
              <dd>{{ selectedAsset.block_count }}</dd>
            </div>
            <div v-if="hasPages(selectedAsset.media_kind)">
              <dt class="source-fact-label">
                {{ i18n.t("pdf_corpus.source_stat_ocr") }}
                <UiTooltip :text="i18n.t('pdf_corpus.source_ocr_pages_help')" placement="bottom" />
              </dt>
              <dd>{{ selectedAsset.ocr_pages }}</dd>
            </div>
          </dl>
          <dl class="source-facts">
            <div>
              <dt>{{ i18n.t("pdf_corpus.loaded") }}</dt>
              <dd>{{ formatDate(selectedAsset.created_at) }}</dd>
            </div>
            <div>
              <dt>SHA-256</dt>
              <dd class="hash">
                <code>{{ selectedAsset.sha256.slice(0, 16) }}…</code>
                <button
                  type="button"
                  class="hash-copy"
                  :aria-label="i18n.t('pdf_corpus.source_copy_hash')"
                  @click="copyHash"
                >
                  <AppIcon :name="copied ? 'check' : 'copy'" />
                </button>
                <span class="sr-only" role="status">{{
                  copied ? i18n.t("pdf_corpus.source_hash_copied") : ""
                }}</span>
              </dd>
            </div>
            <div v-if="selectedAsset.deterministic_checked_at" class="check-row">
              <dt class="source-fact-label">
                {{ i18n.t("pdf_corpus.deterministic_check") }}
                <UiTooltip
                  :text="i18n.t('pdf_corpus.deterministic_check_help')"
                  placement="bottom"
                />
              </dt>
              <dd>
                <span
                  ><small>{{ i18n.t("pdf_corpus.initial_title", "Title") }}</small>
                  {{ selectedAsset.initial_metadata?.title || unset() }}</span
                >
                <span
                  ><small>{{ i18n.t("pdf_corpus.initial_author", "Author") }}</small>
                  {{ selectedAsset.initial_metadata?.document_author || unset() }}</span
                >
                <span
                  ><small>{{ i18n.t("pdf_corpus.initial_speaker", "Speaker") }}</small>
                  {{ selectedAsset.initial_metadata?.speaker || unset() }}</span
                >
              </dd>
            </div>
          </dl>
          <p
            v-if="selectedAsset.page_number_detection"
            class="page-detect-result"
            :data-status="selectedAsset.page_number_detection.status"
            role="status"
          >
            <AppIcon
              :name="
                selectedAsset.page_number_detection.status === 'detected' ? 'check' : 'warning'
              "
            />
            {{ pageDetectionText(selectedAsset.page_number_detection) }}
          </p>
          <button type="button" class="btn primary continue" @click="emit('continue')">
            {{ i18n.t("pdf_corpus.source_continue") }}
            <span aria-hidden="true">→</span>
          </button>
        </article>
        <div v-else class="source-empty">
          <span class="empty-orb" aria-hidden="true"><AppIcon name="spark" /></span>
          <strong>{{ i18n.t("pdf_corpus.source_empty_title") }}</strong>
          <p>{{ i18n.t("pdf_corpus.source_empty_help") }}</p>
        </div>
      </section>
    </div>

    <section v-if="assets.length" class="saved-sources" aria-labelledby="source-saved-title">
      <header class="saved-head">
        <h4 id="source-saved-title" class="stage-title">
          <AppIcon name="history" />
          {{ i18n.t("pdf_corpus.source_library_title") }}
          <span class="count-chip">{{ assets.length }}</span>
        </h4>
      </header>
      <div v-if="confirmingDelete" class="saved-confirm" role="group">
        <span>{{
          i18n.tf("pdf_corpus.source_delete_named", { name: deleteName(confirmingDelete) })
        }}</span>
        <span>{{ i18n.t("pdf_corpus.source_delete_confirm") }}</span>
        <button type="button" class="btn danger" @click="confirmDelete(confirmingDelete)">
          {{ i18n.t("pdf_corpus.source_delete") }}
        </button>
        <button type="button" class="btn" @click="confirmingDelete = ''">
          {{ i18n.t("ui.cancel") }}
        </button>
      </div>
      <SourceTable
        compact
        deletable
        :active-id="assetId"
        :queued-ids="queuedSourceIds"
        :disabled="sourceSetupDisabled"
        :locked-reason="sourceSelectionDisabled ? i18n.t('pdf_corpus.source_locked_help') : ''"
        :refresh-key="assetsKey"
        :page-size="10"
        @choose="emit('update:assetId', $event)"
        @inspect="inspectedSource = $event"
        @delete="confirmingDelete = $event"
      />
      <SourceInspector
        v-if="inspectedSource"
        :source-id="inspectedSource"
        @close="inspectedSource = ''"
      />
    </section>

    <CorpusCaptureDialog
      v-if="captureOpen"
      :open="captureOpen"
      @close="captureOpen = false"
      @changed="onCaptureChanged"
      @use-in-builder="useCaptured"
      @view-sources="emit('viewCaptureSources', $event)"
    />

    <CorpusImportShell
      :open="importShellOpen"
      :default-mode="importShellMode"
      :disabled="disabled"
      @close="importShellOpen = false"
      @choose="selectImportMode"
    />

    <CorpusLibrarySearch
      v-if="searchOpen"
      :query="gutenbergQuery"
      :language="wikisourceLanguage"
      :gutenberg-hits="hits"
      :wikisource-hits="wikisourceHits"
      :gutenberg-status="gutenbergStatus"
      :searched="librarySearched"
      :busy="busy"
      :error="libraryError"
      :importing="libraryImporting"
      :imported="libraryImported"
      :disabled="disabled"
      @update:query="emit('update:gutenbergQuery', $event)"
      @update:language="emit('update:wikisourceLanguage', $event)"
      @search="
        (library) => (library === 'gutenberg' ? emit('searchGutenberg') : emit('searchWikisource'))
      "
      @import-gutenberg="emit('importGutenberg', $event)"
      @import-wikisource="emit('importWikisource', $event)"
      @refresh-gutenberg-status="emit('refreshGutenbergStatus')"
      @refresh-gutenberg-catalogue="emit('refreshGutenbergCatalogue')"
      @update-gutenberg-archive="emit('updateGutenbergArchive', $event)"
      @close="searchOpen = false"
    />
    <UiDialog
      v-if="languagePrompt"
      :open="true"
      :title="i18n.t('pdf_corpus.language_prompt_title')"
      :description="
        i18n.tf('pdf_corpus.language_prompt_help', { filename: languagePrompt.filename })
      "
      :dismissible="false"
      size="medium"
    >
      <div class="language-prompt">
        <p v-if="languagePrompt.loading" class="language-prompt-status" role="status">
          {{ i18n.t("pdf_corpus.language_prompt_checking") }}
        </p>
        <p v-else-if="languagePrompt.error" class="language-prompt-status" role="alert">
          {{ languagePrompt.error }}
        </p>
        <label class="language-prompt-field">
          <span>{{ i18n.t("pdf_corpus.language_prompt_label") }}</span>
          <UiCombobox
            v-model="languageDraft"
            :options="languageOptions"
            :recommended="languagePrompt.suggestion ? [languagePrompt.suggestion] : []"
            :recommended-label="i18n.t('pdf_corpus.language_prompt_suggested')"
            :label="i18n.t('pdf_corpus.language_prompt_label')"
            :placeholder="i18n.t('pdf_corpus.language_prompt_placeholder')"
            :disabled="languagePrompt.loading"
            allow-custom
          />
        </label>
        <p v-if="languagePrompt.suggestion" class="language-prompt-suggestion">
          {{
            i18n.tf("pdf_corpus.language_prompt_proposal", {
              language: languageName(languagePrompt.suggestion, i18n.locale),
              confidence:
                languagePrompt.confidence == null
                  ? "—"
                  : `${Math.round(languagePrompt.confidence * 100)}%`,
            })
          }}
        </p>
      </div>
      <template #footer>
        <UiButton
          variant="ghost"
          :label="i18n.t('pdf_corpus.language_prompt_skip')"
          :disabled="languagePrompt.loading"
          @click="emit('save-language', null)"
        />
        <UiButton
          variant="primary"
          :label="i18n.t('pdf_corpus.language_prompt_save')"
          :disabled="languagePrompt.loading || !languageDraft.trim()"
          @click="emit('save-language', languageDraft.trim().toLowerCase().replaceAll('_', '-'))"
        />
      </template>
    </UiDialog>
  </div>
</template>
<style scoped>
.source-ingest {
  display: grid;
  gap: var(--space-5, 20px);
}

.language-prompt {
  display: grid;
  gap: var(--space-4, 16px);
}

.language-prompt-field {
  display: grid;
  gap: var(--space-2, 8px);
  color: var(--text-primary);
  font-weight: 600;
}

.language-prompt-status,
.language-prompt-suggestion {
  margin: 0;
  color: var(--text-secondary);
}

/* Two-stage layout: add a source, then see what you are working with. */
.source-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: var(--space-5, 20px);
  align-items: start;
}
.add-source,
.current-source {
  display: grid;
  gap: var(--space-3, 12px);
  min-width: 0;
}
.stage-title {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin: 0;
  font-size: var(--fs-md);
  font-weight: var(--fw-bold);
  letter-spacing: -0.01em;
}
.stage-step {
  display: inline-grid;
  place-items: center;
  inline-size: 24px;
  block-size: 24px;
  border-radius: var(--radius-pill);
  color: var(--accent-on);
  background: var(--ui-accent, var(--accent));
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}

/* Reading strategy: a segmented choice, decided before a file is added. */
.ocr-choice {
  display: grid;
  gap: var(--space-2, 8px);
  min-inline-size: 0;
  margin: 0;
  padding: 0;
  border: 0;
}
.ocr-choice legend {
  padding: 0;
  font-weight: var(--fw-bold);
}
.ocr-choice > small {
  color: var(--text-tertiary);
  line-height: var(--lh-normal);
}
.ocr-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2, 8px);
}
.ocr-options label {
  position: relative;
  font-weight: var(--fw-regular);
  display: grid;
  gap: 2px;
  align-content: start;
  padding: 10px 12px 10px 38px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}
.ocr-options label:hover {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
}
.ocr-options label.is-selected {
  border-color: var(--ui-accent, var(--accent));
  background: var(--surface-selected);
  box-shadow: 0 0 0 1px var(--ui-accent, var(--accent));
}
.ocr-options input[type="radio"] {
  position: absolute;
  inset-block-start: 12px;
  inset-inline-start: 12px;
  inline-size: 18px;
  block-size: 18px;
  margin: 0;
  accent-color: var(--ui-accent, var(--accent));
}
.ocr-option-title {
  font-size: var(--fs-base);
  font-weight: var(--fw-semibold);
  line-height: var(--lh-tight);
}
.ocr-option-help {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.ocr-options label:has(input:focus-visible) {
  outline: var(--focus-ring-width) solid var(--ui-accent, var(--accent));
  outline-offset: var(--focus-ring-offset);
}

/* Drop zone */
.dropzone {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: 34px 20px 28px;
  border: 2px dashed var(--border-interactive);
  border-radius: var(--radius-overlay);
  color: var(--text);
  background:
    radial-gradient(
      120% 140% at 50% 0%,
      color-mix(in srgb, var(--ui-accent, var(--accent)) 12%, transparent),
      transparent 62%
    ),
    var(--surface-card);
  text-align: center;
  cursor: pointer;
  overflow: hidden;
  transition:
    border-color var(--motion-base) var(--ease-standard),
    background-color var(--motion-base) var(--ease-standard),
    transform var(--motion-base) var(--ease-standard),
    box-shadow var(--motion-base) var(--ease-standard);
}
.dropzone:hover:not(:disabled) {
  border-color: var(--ui-accent, var(--accent));
  box-shadow: var(--shadow-card);
}
.dropzone.is-over {
  border-style: solid;
  border-color: var(--ui-accent, var(--accent));
  background: var(--surface-selected);
  transform: scale(1.012);
  box-shadow: var(--elev-2);
}
.dropzone:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.dropzone-icon {
  display: grid;
  place-items: center;
  inline-size: 60px;
  block-size: 60px;
  border-radius: var(--radius-pill);
  color: var(--accent-on);
  background: var(--ui-accent, var(--accent));
  box-shadow: var(--elev-2);
  transition: transform var(--motion-base) var(--ease-standard);
}
.dropzone-icon svg {
  inline-size: 30px;
  block-size: 30px;
}
.dropzone:hover:not(:disabled) .dropzone-icon,
.dropzone.is-over .dropzone-icon {
  transform: translateY(-3px);
}
.dropzone-title {
  font-size: var(--fs-xl);
  font-weight: var(--fw-bold);
  letter-spacing: -0.015em;
  line-height: var(--lh-tight);
}
.dropzone-sub {
  color: var(--accent-fg);
  font-weight: var(--fw-semibold);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.source-loading {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: center;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-base);
}
.source-loading .spinner {
  margin: 0;
}
.saved-confirm {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  align-items: center;
  margin-block-start: var(--space-2, 8px);
  font-size: var(--fs-sm);
}
.dropzone-progress {
  position: absolute;
  inset-inline: 0;
  inset-block-end: 0;
  block-size: 4px;
  background: linear-gradient(90deg, transparent, var(--ui-accent, var(--accent)), transparent);
  background-size: 40% 100%;
  background-repeat: no-repeat;
  animation: source-sweep 1.2s var(--ease-standard) infinite;
}
@keyframes source-sweep {
  from {
    background-position: -40% 0;
  }
  to {
    background-position: 140% 0;
  }
}
.format-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.format-chips li {
  padding: 2px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  background: var(--surface-inset);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.auto-detect-note {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  text-align: center;
}

/* Other ways in */
.source-paths {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: var(--space-2, 8px);
}
.path-card {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  color: var(--text);
  background: var(--surface-card);
  text-align: start;
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}
.path-card:hover:not(:disabled) {
  border-color: var(--ui-accent, var(--accent));
  box-shadow: var(--shadow-card);
  transform: translateY(-1px);
}
.path-card[aria-expanded="true"] {
  border-color: var(--ui-accent, var(--accent));
  background: var(--surface-selected);
}
.path-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.path-icon {
  display: grid;
  place-items: center;
  flex: none;
  inline-size: 40px;
  block-size: 40px;
  border-radius: var(--radius-control);
  color: var(--accent-fg);
  background: var(--surface-selected);
}
.path-icon svg {
  inline-size: 22px;
  block-size: 22px;
}
.path-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.path-copy strong {
  font-size: var(--fs-base);
  line-height: var(--lh-tight);
}
.path-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.url-source {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto;
  gap: var(--space-2, 8px);
  align-items: end;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
}
.url-source label {
  display: grid;
  gap: 5px;
}
.url-detect svg {
  inline-size: 14px;
  block-size: 14px;
}
.url-detect {
  display: flex;
  grid-column: 1 / -1;
  gap: 6px;
  align-items: center;
  margin: 0;
  color: var(--tone-ok-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}

/* Current source */
.source-card {
  align-self: start;
  display: grid;
  gap: var(--space-3, 12px);
  padding: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--ui-accent, var(--accent)) 8%, transparent),
      transparent 90px
    ),
    var(--surface-card);
  box-shadow: var(--shadow-card);
  animation: source-rise var(--motion-base) var(--ease-standard);
}
@keyframes source-rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
.source-card-head {
  display: flex;
  gap: 12px;
  align-items: center;
  min-width: 0;
}
.source-card-head h5 {
  margin: 0;
  font-family: var(--font-reading);
  font-size: var(--fs-lg);
  font-weight: var(--fw-semibold);
  line-height: var(--lh-tight);
  overflow-wrap: anywhere;
}
.source-card-head p {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 4px 0 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.kind-mark {
  display: grid;
  place-items: center;
  flex: none;
  inline-size: 44px;
  block-size: 52px;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-control);
  color: var(--accent-fg);
  background: var(--surface-selected);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
}
.ready-chip {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  padding: 1px 8px;
  border: 1px solid var(--tone-ok-edge);
  border-radius: var(--radius-pill);
  color: var(--tone-ok-fg);
  background: var(--tone-ok-bg);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
}
.ready-chip svg {
  inline-size: 12px;
  block-size: 12px;
}
.stat-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: var(--space-2, 8px);
  margin: 0;
}
.stat-tiles div {
  display: grid;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.stat-tiles dt {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.stat-tiles dd {
  margin: 0;
  font-size: var(--fs-xl);
  font-weight: var(--fw-bold);
  font-variant-numeric: tabular-nums;
  line-height: var(--lh-tight);
}
.source-facts {
  display: grid;
  gap: 8px;
  margin: 0;
  font-size: var(--fs-sm);
}
.source-facts > div {
  display: grid;
  grid-template-columns: minmax(96px, auto) 1fr;
  gap: 10px;
  align-items: baseline;
}
.source-facts dt {
  color: var(--text-tertiary);
  font-weight: var(--fw-semibold);
}
.source-facts dd {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}
.check-row dd small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  margin-inline-end: 4px;
}
.check-row dd span {
  padding: 1px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
}
.hash code {
  font-family: var(--font-mono);
}
.hash-copy {
  display: inline-grid;
  place-items: center;
  inline-size: 28px;
  block-size: 28px;
  padding: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  color: var(--text-secondary);
  background: var(--surface-card);
  cursor: pointer;
}
.hash-copy:hover {
  border-color: var(--border-interactive);
  color: var(--accent-fg);
}
.hash-copy svg {
  inline-size: 14px;
  block-size: 14px;
}
.source-fact-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.source-facts-help {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.continue {
  justify-self: start;
  gap: 8px;
}
.page-detect {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  cursor: pointer;
}
.page-detect.is-on {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.page-detect input {
  inline-size: 18px;
  block-size: 18px;
  margin: 2px 0 0;
  accent-color: var(--ui-accent, var(--accent));
}
.page-detect-copy {
  display: grid;
  gap: 2px;
}
.page-detect-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.page-detect-result {
  display: flex;
  gap: 8px;
  align-items: center;
  margin: 0;
  color: var(--tone-ok-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.page-detect-result[data-status="not_found"],
.page-detect-result[data-status="disabled"] {
  color: var(--tone-warn-fg);
}
.page-detect-result svg {
  inline-size: 14px;
  block-size: 14px;
  flex: none;
}
.source-empty {
  display: grid;
  align-content: center;
  min-block-size: 280px;
  justify-items: center;
  gap: 8px;
  padding: 36px 24px;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-overlay);
  color: var(--text-secondary);
  background: var(--surface-inset);
  text-align: center;
}
.source-empty p {
  max-inline-size: 36ch;
  margin: 0;
  color: var(--text-tertiary);
  line-height: var(--lh-normal);
}
.empty-orb {
  display: grid;
  place-items: center;
  inline-size: 56px;
  block-size: 56px;
  border-radius: var(--radius-pill);
  color: var(--accent-fg);
  background: var(--surface-selected);
}
.empty-orb svg {
  inline-size: 28px;
  block-size: 28px;
}

/* Saved sources */
.saved-sources {
  display: grid;
  gap: var(--space-3, 12px);
  padding-block-start: var(--space-4, 16px);
  border-block-start: 1px solid var(--border-subtle);
}
.saved-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.saved-head .stage-title svg {
  inline-size: 16px;
  block-size: 16px;
}
.count-chip {
  padding: 0 8px;
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  background: var(--surface-inset);
  font-size: var(--fs-xs);
}

.source-ingest :is(button, input, select):focus-visible {
  outline: var(--focus-ring-width) solid var(--ui-accent, var(--accent));
  outline-offset: var(--focus-ring-offset);
}

@media (max-width: 1080px) {
  .source-stage {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .ocr-options,
  .url-source {
    grid-template-columns: 1fr;
  }
  .dropzone {
    padding: 26px 14px 22px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .dropzone,
  .dropzone-icon,
  .path-card,
  .ocr-options label {
    transition: none;
  }
  .source-card,
  .dropzone-progress {
    animation: none;
  }
  .dropzone.is-over {
    transform: none;
  }
  .path-card:hover:not(:disabled),
  .dropzone:hover:not(:disabled) .dropzone-icon {
    transform: none;
  }
}
</style>

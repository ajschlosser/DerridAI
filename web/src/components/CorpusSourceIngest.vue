<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { GutenbergHit, PdfAsset, WikisourceHit, GutenbergStatus } from "../api/corpus";

import { hasPages } from "../domain/sourceMedia";
import AppIcon from "./AppIcon.vue";
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
    sourceUrl?: string;
    gutenbergQuery?: string;
    hits?: GutenbergHit[];
    wikisourceHits?: WikisourceHit[];
    gutenbergStatus?: GutenbergStatus | null;
    selectedAsset?: PdfAsset | null;
    disabled?: boolean;
    sourceSelectionDisabled?: boolean;
    busy?: string;
  }>(),
  {
    assets: () => [],
    assetId: "",
    illegibility: 0,
    detectPageNumbers: true,
    sourceUrl: "",
    gutenbergQuery: "",
    hits: () => [],
    wikisourceHits: () => [],
    gutenbergStatus: null,
    selectedAsset: null,
    disabled: false,
    sourceSelectionDisabled: false,
    busy: "",
  },
);

const emit = defineEmits<{
  "update:assetId": [string];
  "update:illegibility": [number];
  "update:detectPageNumbers": [boolean];
  "update:sourceUrl": [string];
  "update:gutenbergQuery": [string];
  useCurrent: [];
  file: [File];
  loadUrl: [];
  searchGutenberg: [];
  searchWikisource: [];
  refreshGutenbergStatus: [];
  refreshGutenbergCatalogue: [];
  updateGutenbergArchive: [action: "start" | "pause" | "resume" | "refetch"];
  importGutenberg: [number];
  continue: [];
}>();

const i18n = useI18nStore();
const uploadInput = ref<HTMLInputElement | null>(null);
const searchOpen = ref(false);
const searchDialog = ref<HTMLDialogElement | null>(null);
const statusPoll = ref<number | null>(null);
const activeLibrary = ref<"gutenberg" | "wikisource">("gutenberg");

const sourceSetupDisabled = computed(() => props.disabled || props.sourceSelectionDisabled);
const catalogueRefreshing = computed(() =>
  ["refreshing", "indexing"].includes(String(props.gutenbergStatus?.catalogue.status || "")),
);
const archiveStatus = computed(() => String(props.gutenbergStatus?.archive.status || ""));
const archiveSettling = computed(() =>
  ["downloaded", "unpacking", "ready"].includes(archiveStatus.value),
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

function formatShortDate(value?: string | null) {
  if (!value) return unset();
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, { dateStyle: "medium" }).format(
      new Date(value),
    );
  } catch {
    return value;
  }
}

function formatBytes(value?: number | null) {
  const bytes = Math.max(0, Number(value || 0));
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = bytes;
  let unit = -1;
  do {
    size /= 1024;
    unit += 1;
  } while (size >= 1024 && unit < units.length - 1);
  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unit]}`;
}

function archiveAction(): "start" | "pause" | "resume" {
  if (archiveStatus.value === "downloading") return "pause";
  if (archiveStatus.value === "paused") return "resume";
  return "start";
}

function archiveActionLabel() {
  if (archiveStatus.value === "ready") {
    return i18n.t("pdf_corpus.gutenberg_collection_ready", "Collection ready");
  }
  if (["downloaded", "unpacking"].includes(archiveStatus.value)) {
    return i18n.t("pdf_corpus.gutenberg_unpacking", "Unpacking collection…");
  }
  if (archiveStatus.value === "downloading") {
    return i18n.t("pdf_corpus.gutenberg_pause_download");
  }
  if (archiveStatus.value === "paused") {
    return i18n.t("pdf_corpus.gutenberg_resume_download");
  }
  return i18n.t("pdf_corpus.gutenberg_start_download");
}

function catalogueActionLabel() {
  if (catalogueRefreshing.value) {
    return i18n.t("pdf_corpus.gutenberg_catalogue_refreshing", "Updating catalogue…");
  }
  return i18n.t(
    props.gutenbergStatus?.catalogue.status === "ready"
      ? "pdf_corpus.gutenberg_refetch_catalogue"
      : "pdf_corpus.gutenberg_fetch_catalogue",
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

function importLabel(hit: GutenbergHit) {
  return i18n.tf("pdf_corpus.import_gutenberg_hit", {
    title: hit.title,
    author: hit.author || unset(),
    id: hit.etext_id,
    language: hit.language,
  });
}

async function openSearch() {
  searchOpen.value = true;
  emit("refreshGutenbergStatus");
  await nextTick();
  const dialog = searchDialog.value;
  if (dialog && !dialog.open) {
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }
  if (statusPoll.value === null) {
    statusPoll.value = window.setInterval(() => emit("refreshGutenbergStatus"), 2000);
  }
}

function closeSearch() {
  const dialog = searchDialog.value;
  if (dialog?.open && typeof dialog.close === "function") dialog.close();
  searchOpen.value = false;
  if (statusPoll.value !== null) {
    window.clearInterval(statusPoll.value);
    statusPoll.value = null;
  }
}

onBeforeUnmount(closeSearch);

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
const libraryFilter = ref("");
const FILTER_THRESHOLD = 6;
const visibleAssets = computed(() => {
  const needle = libraryFilter.value.trim().toLowerCase();
  return needle
    ? props.assets.filter((asset) => asset.filename.toLowerCase().includes(needle))
    : props.assets;
});
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

        <fieldset class="ocr-choice" :disabled="sourceSetupDisabled">
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

        <label class="page-detect" :class="{ 'is-on': detectPageNumbers }">
          <input
            type="checkbox"
            :checked="detectPageNumbers"
            :disabled="sourceSetupDisabled"
            @change="emit('update:detectPageNumbers', ($event.target as HTMLInputElement).checked)"
          />
          <span class="page-detect-copy">
            <strong>{{ i18n.t("pdf_corpus.source_page_detect") }}</strong>
            <small>{{ i18n.t("pdf_corpus.source_page_detect_help") }}</small>
          </span>
        </label>

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
              <dt>{{ i18n.t("pdf_corpus.source_stat_units") }}</dt>
              <dd>{{ selectedAsset.block_count }}</dd>
            </div>
            <div v-if="hasPages(selectedAsset.media_kind)">
              <dt>{{ i18n.t("pdf_corpus.source_stat_ocr") }}</dt>
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
              <dt>{{ i18n.t("pdf_corpus.deterministic_check") }}</dt>
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
          <p class="source-facts-help">{{ i18n.t("pdf_corpus.source_facts_help") }}</p>
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
        <label v-if="assets.length >= FILTER_THRESHOLD" class="saved-filter">
          <span class="sr-only">{{ i18n.t("pdf_corpus.source_library_filter") }}</span>
          <input
            v-model="libraryFilter"
            class="control"
            type="search"
            :placeholder="i18n.t('pdf_corpus.source_library_filter')"
          />
        </label>
      </header>
      <p v-if="sourceSelectionDisabled" class="saved-locked" role="status">
        <AppIcon name="lock" />{{ i18n.t("pdf_corpus.source_locked_help") }}
      </p>
      <ul class="saved-grid" role="list">
        <li v-for="asset in visibleAssets" :key="asset.asset_id">
          <button
            type="button"
            class="saved-card"
            :class="{ 'is-selected': asset.asset_id === assetId }"
            :aria-pressed="asset.asset_id === assetId"
            :disabled="sourceSetupDisabled"
            @click="emit('update:assetId', asset.asset_id === assetId ? '' : asset.asset_id)"
          >
            <span class="kind-mark" aria-hidden="true">{{ kindMark(asset) }}</span>
            <span class="saved-copy">
              <strong>{{ asset.filename }}</strong>
              <small
                >{{ asset.block_count }} {{ i18n.t("pdf_corpus.source_stat_units_short") }} ·
                {{ formatShortDate(asset.created_at) }}</small
              >
            </span>
            <span v-if="asset.asset_id === assetId" class="saved-check" aria-hidden="true"
              ><AppIcon name="check"
            /></span>
          </button>
        </li>
      </ul>
      <p v-if="!visibleAssets.length" class="saved-none">
        {{ i18n.t("pdf_corpus.source_library_none") }}
      </p>
    </section>

    <dialog
      v-if="searchOpen"
      ref="searchDialog"
      class="source-search-dialog"
      aria-labelledby="source-search-title"
      @cancel.prevent="closeSearch"
    >
      <div class="source-search-dialog__header">
        <div>
          <p class="eyebrow">{{ i18n.t("pdf_corpus.source_setup_title") }}</p>
          <h2 id="source-search-title">
            {{ i18n.t("pdf_corpus.search_library", "Search digital libraries") }}
          </h2>
          <p class="source-search-dialog__lede">
            {{ i18n.t("pdf_corpus.search_library_help") }}
          </p>
        </div>
        <button
          type="button"
          class="btn btn-icon"
          :aria-label="i18n.t('common.close')"
          @click="closeSearch"
        >
          ×
        </button>
      </div>
      <div class="library-tabs" role="tablist" :aria-label="i18n.t('pdf_corpus.search_library')">
        <button
          type="button"
          class="library-tab"
          :class="{ 'is-active': activeLibrary === 'gutenberg' }"
          role="tab"
          :aria-selected="activeLibrary === 'gutenberg'"
          @click="activeLibrary = 'gutenberg'"
        >
          <span class="library-tab__mark">G</span>
          <span
            ><strong>{{ i18n.t("pdf_corpus.project_gutenberg") }}</strong
            ><small>{{
              gutenbergStatus?.search_ready
                ? i18n.t("pdf_corpus.gutenberg_catalogue_ready")
                : i18n.t("pdf_corpus.gutenberg_catalogue_not_ready")
            }}</small></span
          >
        </button>
        <button
          type="button"
          class="library-tab"
          :class="{ 'is-active': activeLibrary === 'wikisource' }"
          role="tab"
          :aria-selected="activeLibrary === 'wikisource'"
          @click="activeLibrary = 'wikisource'"
        >
          <span class="library-tab__mark">W</span>
          <span
            ><strong>{{ i18n.t("pdf_corpus.wikisource") }}</strong
            ><small>{{ i18n.t("pdf_corpus.wikisource_search") }}</small></span
          >
        </button>
      </div>
      <div v-if="activeLibrary === 'gutenberg'" class="library-status" role="status">
        <span v-if="gutenbergStatus?.search_ready"
          >{{ gutenbergStatus.catalogue.item_count }}
          {{ i18n.t("pdf_corpus.gutenberg_catalogue_ready") }}</span
        >
        <span v-else>{{ i18n.t("pdf_corpus.gutenberg_catalogue_not_ready") }}</span>
        <div class="library-status__actions">
          <button
            type="button"
            class="btn btn-quiet"
            :disabled="disabled || busy === 'gutenberg-catalogue' || catalogueRefreshing"
            @click="emit('refreshGutenbergCatalogue')"
          >
            {{ catalogueActionLabel() }}
          </button>
          <button
            type="button"
            class="btn btn-quiet"
            :disabled="disabled || busy === 'gutenberg-archive' || archiveSettling"
            @click="emit('updateGutenbergArchive', archiveAction())"
          >
            {{ archiveActionLabel() }}
          </button>
        </div>
        <progress
          v-if="gutenbergStatus?.archive.total_bytes"
          class="archive-progress"
          :value="gutenbergStatus.archive.bytes_done"
          :max="gutenbergStatus.archive.total_bytes"
          :aria-label="i18n.t('pdf_corpus.gutenberg_download_progress')"
        />
        <small v-if="gutenbergStatus?.archive.total_bytes" class="library-note">
          {{ formatBytes(gutenbergStatus.archive.bytes_done) }} /
          {{ formatBytes(gutenbergStatus.archive.total_bytes) }}
        </small>
        <small v-if="gutenbergStatus?.search_ready && !gutenbergStatus?.ready" class="library-note">
          {{
            i18n.t(
              "pdf_corpus.gutenberg_results_locked",
              "Catalogue search is ready. Results become importable after the full text collection finishes downloading and unpacking.",
            )
          }}
        </small>
        <small v-if="gutenbergStatus?.catalogue.error" class="source-error">{{
          gutenbergStatus.catalogue.error
        }}</small>
        <small v-if="gutenbergStatus?.archive.error" class="source-error">{{
          gutenbergStatus.archive.error
        }}</small>
      </div>
      <form
        class="gutenberg-source"
        @submit.prevent="
          activeLibrary === 'gutenberg' ? emit('searchGutenberg') : emit('searchWikisource')
        "
      >
        <label for="pdf-corpus-gutenberg">
          <span>{{
            activeLibrary === "gutenberg"
              ? i18n.t("pdf_corpus.gutenberg_search")
              : i18n.t("pdf_corpus.wikisource_search")
          }}</span>
          <input
            id="pdf-corpus-gutenberg"
            class="control"
            type="search"
            :value="gutenbergQuery"
            :placeholder="i18n.t('pdf_corpus.gutenberg_query')"
            :disabled="disabled"
            @input="emit('update:gutenbergQuery', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <button
          type="submit"
          class="btn primary"
          :disabled="
            disabled ||
            !gutenbergQuery.trim() ||
            (activeLibrary === 'gutenberg' && !gutenbergStatus?.search_ready)
          "
        >
          {{
            busy === "gutenberg"
              ? i18n.t("pdf_corpus.extracting")
              : activeLibrary === "gutenberg"
                ? i18n.t("pdf_corpus.gutenberg_search")
                : i18n.t("pdf_corpus.wikisource_search")
          }}
        </button>
      </form>
      <ul
        v-if="hits.length"
        class="gutenberg-hits"
        :aria-label="i18n.t('pdf_corpus.gutenberg_results')"
      >
        <li v-for="hit in hits" :key="hit.etext_id">
          <button
            type="button"
            class="btn"
            :disabled="disabled || !gutenbergStatus?.ready"
            :title="
              gutenbergStatus?.ready
                ? undefined
                : i18n.t(
                    'pdf_corpus.gutenberg_result_unavailable',
                    'Download and unpack the collection before importing this result.',
                  )
            "
            :aria-label="importLabel(hit)"
            @click="emit('importGutenberg', hit.etext_id)"
          >
            <span>{{ hit.title }}</span>
            <small>{{ hit.author }} · #{{ hit.etext_id }} · {{ hit.language }}</small>
          </button>
        </li>
      </ul>
      <ul v-if="wikisourceHits.length" class="gutenberg-hits" aria-label="Wikisource results">
        <li v-for="hit in wikisourceHits" :key="hit.page_id">
          <button
            type="button"
            class="btn"
            :disabled="disabled"
            @click="
              emit('update:sourceUrl', hit.url);
              emit('loadUrl');
            "
          >
            <span>{{ hit.title }}</span>
            <small>{{ hit.snippet }}</small>
          </button>
        </li>
      </ul>
      <div class="source-search-dialog__footer">
        <button type="button" class="btn" @click="closeSearch">
          {{ i18n.t("common.close", "Close") }}
        </button>
      </div>
    </dialog>
  </div>
</template>
<style scoped>
.source-ingest {
  display: grid;
  gap: var(--space-5, 20px);
}

/* Two-stage layout: add a source, then see what you are working with. */
.source-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: var(--space-5, 20px);
  align-items: stretch;
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
.current-source {
  grid-template-rows: auto 1fr;
}
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
.saved-filter {
  inline-size: min(260px, 100%);
}
.saved-locked {
  display: flex;
  gap: 6px;
  align-items: center;
  margin: 0;
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
}
.saved-locked svg {
  inline-size: 14px;
  block-size: 14px;
}
.saved-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: var(--space-2, 8px);
  margin: 0;
  padding: 0;
  list-style: none;
}
.saved-card {
  position: relative;
  display: flex;
  gap: 12px;
  align-items: center;
  inline-size: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  color: var(--text);
  background: var(--surface-card);
  text-align: start;
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}
.saved-card:hover:not(:disabled) {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
  transform: translateY(-1px);
}
.saved-card.is-selected {
  border-color: var(--ui-accent, var(--accent));
  background: var(--surface-selected);
  box-shadow: 0 0 0 1px var(--ui-accent, var(--accent));
}
.saved-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.saved-card .kind-mark {
  inline-size: 38px;
  block-size: 44px;
}
.saved-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.saved-copy strong {
  overflow: hidden;
  font-size: var(--fs-base);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.saved-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.saved-check {
  display: grid;
  place-items: center;
  flex: none;
  inline-size: 22px;
  block-size: 22px;
  margin-inline-start: auto;
  border-radius: var(--radius-pill);
  color: var(--accent-on);
  background: var(--ui-accent, var(--accent));
  animation: source-pop var(--motion-base) var(--ease-standard);
}
.saved-check svg {
  inline-size: 14px;
  block-size: 14px;
}
@keyframes source-pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
}
.saved-none {
  margin: 0;
  color: var(--text-tertiary);
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
  .saved-card,
  .ocr-options label {
    transition: none;
  }
  .source-card,
  .saved-check,
  .dropzone-progress {
    animation: none;
  }
  .dropzone.is-over {
    transform: none;
  }
  .path-card:hover:not(:disabled),
  .saved-card:hover:not(:disabled),
  .dropzone:hover:not(:disabled) .dropzone-icon {
    transform: none;
  }
  .source-search-dialog::backdrop {
    backdrop-filter: none;
  }
}

/* Digital-library search dialog */
.source-setup-grid > label,
.ingest-actions,
.illegibility-field,
.url-source label,
.gutenberg-source label {
  display: grid;
  gap: 5px;
}
.source-search-dialog {
  inline-size: min(760px, calc(100vw - 32px));
  max-block-size: min(760px, calc(100vh - 32px));
  margin: auto;
  padding: 24px;
  border: 1px solid var(--border-strong, var(--border));
  border-radius: 20px;
  color: var(--text);
  background: var(--surface-raised);
  box-shadow: var(--shadow-lg);
  overflow: auto;
}
.source-search-dialog::backdrop {
  background: rgb(8 12 20 / 68%);
  backdrop-filter: blur(4px);
}
.source-search-dialog__header,
.source-search-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.source-search-dialog__footer {
  justify-content: flex-end;
  margin-block-start: 16px;
}
.source-search-dialog h2 {
  margin: 0;
  font-size: clamp(1.25rem, 2vw, 1.6rem);
  letter-spacing: -0.02em;
}
.source-search-dialog__lede {
  max-inline-size: 52ch;
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.5;
}
.library-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 22px 0 14px;
}
.library-tab {
  display: flex;
  align-items: center;
  gap: 10px;
  min-block-size: 64px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text);
  background: var(--surface);
  text-align: start;
}
.library-tab:hover {
  border-color: var(--accent);
}
.library-tab.is-active {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, var(--surface));
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 22%, transparent);
}
.library-tab__mark {
  display: grid;
  place-items: center;
  inline-size: 32px;
  block-size: 32px;
  border-radius: 9px;
  color: var(--on-accent, var(--surface));
  background: var(--accent);
  font-weight: 800;
}
.library-tab span:last-child {
  display: grid;
  gap: 3px;
}
.library-tab small {
  color: var(--muted);
  font-size: 0.75rem;
}
.library-status {
  display: grid;
  gap: 10px;
  margin-block-end: 14px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.library-status__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn-quiet {
  min-block-size: 32px;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border);
}
.archive-progress {
  inline-size: 100%;
  block-size: 8px;
  accent-color: var(--accent);
}
.source-error {
  color: var(--danger);
  overflow-wrap: anywhere;
}
.eyebrow {
  margin: 0 0 4px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.btn-icon {
  min-inline-size: 36px;
  font-size: 1.25rem;
}
.url-source,
.gutenberg-source {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto;
  gap: 8px;
  align-items: end;
}
.gutenberg-hits {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.gutenberg-hits .btn {
  text-align: start;
  white-space: normal;
}
.source-search-dialog::backdrop {
  backdrop-filter: none;
}
.source-setup-grid,
.url-source,
.gutenberg-source {
  grid-template-columns: 1fr;
}
.source-search-dialog {
  inline-size: calc(100vw - 16px);
  padding: 18px;
  border-radius: 16px;
}
.library-tabs {
  grid-template-columns: 1fr;
}
.gutenberg-source,
.url-source {
  grid-template-columns: 1fr;
}
.gutenberg-source {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto;
  gap: 8px;
  align-items: end;
}
@media (max-width: 760px) {
  .source-search-dialog {
    inline-size: calc(100vw - 16px);
    padding: 18px;
    border-radius: 16px;
  }
  .library-tabs,
  .gutenberg-source {
    grid-template-columns: 1fr;
  }
}
</style>

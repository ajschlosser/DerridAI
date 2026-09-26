<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { GutenbergHit, PdfAsset, WikisourceHit, GutenbergStatus } from "../api/corpus";

import { hasPages } from "../domain/sourceMedia";
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
}>();

const i18n = useI18nStore();
const uploadInput = ref<HTMLInputElement | null>(null);
const searchOpen = ref(false);
const searchDialog = ref<HTMLDialogElement | null>(null);
const statusPoll = ref<number | null>(null);
const activeLibrary = ref<"gutenberg" | "wikisource">("gutenberg");

const sourceSetupDisabled = computed(
  () => props.disabled || props.sourceSelectionDisabled,
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
</script>

<template>
  <div class="source-ingest" :aria-busy="busy ? 'true' : undefined">
    <div class="source-setup-grid">
      <label for="pdf-corpus-source">
        <span>{{ i18n.t("pdf_corpus.source_asset") }}</span>
        <select
          id="pdf-corpus-source"
          class="control"
          :value="assetId"
          :disabled="sourceSetupDisabled"
          @change="emit('update:assetId', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">
            {{ i18n.t("pdf_corpus.choose_persisted_pdf") }}
          </option>
          <option v-for="asset in assets" :key="asset.asset_id" :value="asset.asset_id">
            {{ asset.filename }} · {{ asset.block_count }}
            {{ i18n.t("pdf_corpus.blocks") }}
          </option>
        </select>
      </label>
      <div class="ingest-actions">
        <p class="auto-detect-note">
          {{ i18n.t("pdf_corpus.source_auto_detect") }}
        </p>
        <fieldset class="illegibility-field" :disabled="sourceSetupDisabled">
          <legend>{{ i18n.t("pdf_corpus.source_illegibility") }}</legend>
          <small id="source-illegibility-help">{{
            i18n.t("pdf_corpus.source_illegibility_help")
          }}</small>
          <label>
            <input
              name="source-ocr-strategy"
              type="radio"
              value="embedded"
              :checked="ocrStrategy === 'embedded'"
              @change="onOcrStrategy('embedded')"
            />
            {{ i18n.t("pdf_corpus.source_ocr_embedded") }}
          </label>
          <label>
            <input
              name="source-ocr-strategy"
              type="radio"
              value="difficult"
              :checked="ocrStrategy === 'difficult'"
              @change="onOcrStrategy('difficult')"
            />
            {{ i18n.t("pdf_corpus.source_ocr_difficult") }}
          </label>
          <label>
            <input
              name="source-ocr-strategy"
              type="radio"
              value="always"
              :checked="ocrStrategy === 'always'"
              @change="onOcrStrategy('always')"
            />
            {{ i18n.t("pdf_corpus.source_ocr_always") }}
          </label>
        </fieldset>
        <div class="source-actions">
          <button
            v-if="selectedAsset?.media_kind === 'pdf'"
            type="button"
            class="btn"
            :disabled="sourceSetupDisabled"
            @click="emit('useCurrent')"
          >
            {{ i18n.t("pdf_corpus.use_current_pdf") }}
          </button>
          <button
            type="button"
            class="btn source-choose"
            :disabled="sourceSetupDisabled"
            @click="uploadInput?.click()"
          >
            {{
              busy === "upload" ? i18n.t("pdf_corpus.extracting") : i18n.t("pdf_corpus.choose_pdf")
            }}
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
          <button type="button" class="btn btn-secondary" :disabled="disabled" @click="openSearch">
            {{ i18n.t("pdf_corpus.search_library", "Search digital libraries") }}
          </button>
        </div>
      </div>
    </div>

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
            :disabled="
              disabled ||
              busy === 'gutenberg-catalogue' ||
              ['refreshing', 'indexing'].includes(String(gutenbergStatus?.catalogue.status || ''))
            "
            @click="emit('refreshGutenbergCatalogue')"
          >
            {{
              ["refreshing", "indexing"].includes(
                String(gutenbergStatus?.catalogue.status || ""),
              )
                ? i18n.t("pdf_corpus.gutenberg_catalogue_refreshing", "Updating catalogue…")
                : i18n.t(
                    gutenbergStatus?.catalogue.status === "ready"
                      ? "pdf_corpus.gutenberg_refetch_catalogue"
                      : "pdf_corpus.gutenberg_fetch_catalogue",
                  )
            }}
          </button>
          <button
            type="button"
            class="btn btn-quiet"
            :disabled="
              disabled ||
              busy === 'gutenberg-archive' ||
              ['downloaded', 'unpacking', 'ready'].includes(
                String(gutenbergStatus?.archive.status || ''),
              )
            "
            @click="
              emit(
                'updateGutenbergArchive',
                gutenbergStatus?.archive.status === 'downloading'
                  ? 'pause'
                  : gutenbergStatus?.archive.status === 'paused'
                    ? 'resume'
                    : 'start',
              )
            "
          >
            {{
              gutenbergStatus?.archive.status === "ready"
                ? i18n.t("pdf_corpus.gutenberg_collection_ready", "Collection ready")
                : ["downloaded", "unpacking"].includes(
                      String(gutenbergStatus?.archive.status || ""),
                    )
                  ? i18n.t("pdf_corpus.gutenberg_unpacking", "Unpacking collection…")
                  : i18n.t(
                      gutenbergStatus?.archive.status === "downloading"
                        ? "pdf_corpus.gutenberg_pause_download"
                        : gutenbergStatus?.archive.status === "paused"
                          ? "pdf_corpus.gutenberg_resume_download"
                          : "pdf_corpus.gutenberg_start_download",
                    )
            }}
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
          class="btn btn-primary"
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
      <details class="url-import">
        <summary>{{ i18n.t("pdf_corpus.import_url") }}</summary>
        <form class="url-source" @submit.prevent="emit('loadUrl')">
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
          <button type="submit" class="btn" :disabled="disabled || !sourceUrl.trim()">
            {{ i18n.t("pdf_corpus.load_url") }}
          </button>
        </form>
      </details>
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

    <dl v-if="selectedAsset" class="source-facts">
      <div v-if="selectedAsset.media_kind">
        <dt>{{ i18n.t("pdf_corpus.media_kind") }}</dt>
        <dd>{{ mediaKind(selectedAsset.media_kind) }}</dd>
      </div>
      <div v-if="hasPages(selectedAsset.media_kind)">
        <dt>{{ i18n.t("pdf_corpus.pages") }}</dt>
        <dd>{{ selectedAsset.page_count }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.blocks") }}</dt>
        <dd>{{ selectedAsset.block_count }}</dd>
      </div>
      <div v-if="hasPages(selectedAsset.media_kind)">
        <dt>{{ i18n.t("pdf_corpus.ocr_pages") }}</dt>
        <dd>{{ selectedAsset.ocr_pages }}</dd>
      </div>
      <div>
        <dt>SHA-256</dt>
        <dd>{{ selectedAsset.sha256.slice(0, 16) }}…</dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.loaded") }}</dt>
        <dd>{{ formatDate(selectedAsset.created_at) }}</dd>
      </div>
      <div v-if="selectedAsset.deterministic_checked_at">
        <dt>{{ i18n.t("pdf_corpus.deterministic_check") }}</dt>
        <dd>
          {{ selectedAsset.initial_metadata?.title || unset() }} ·
          {{ selectedAsset.initial_metadata?.document_author || unset() }} ·
          {{ selectedAsset.initial_metadata?.speaker || unset() }}
        </dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.source-ingest {
  display: grid;
  gap: 12px;
}
.source-setup-grid {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(240px, 1fr);
  gap: 12px;
  align-items: end;
}
.source-setup-grid > label,
.ingest-actions,
.illegibility-field,
.url-source label,
.gutenberg-source label {
  display: grid;
  gap: 5px;
}
.ingest-actions {
  gap: 10px;
  align-content: end;
}
.illegibility-field small {
  color: var(--muted);
  line-height: 1.4;
}
.illegibility-field {
  display: grid;
  gap: 8px;
  border: 0;
  padding: 0;
}
.illegibility-field label {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.illegibility-field input[type="radio"] {
  inline-size: 18px;
  block-size: 18px;
  margin: 0;
}
.source-actions,
.alternate-sources {
  display: grid;
  gap: 10px;
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
.url-import {
  margin-block-start: 16px;
  border-block-start: 1px solid var(--border);
  padding-block-start: 14px;
}
.url-import summary {
  color: var(--muted);
  cursor: pointer;
  font-weight: 700;
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
.btn-secondary {
  background: var(--surface-raised);
}
.source-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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
.source-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.source-facts div {
  display: flex;
  gap: 6px;
  min-width: 0;
}
.source-facts dt {
  font-weight: 750;
}
.source-facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.source-ingest :is(button, input, select) {
  min-block-size: 24px;
}
.source-ingest :is(button, input, select):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .source-search-dialog::backdrop {
    backdrop-filter: none;
  }
}
@media (max-width: 760px) {
  .source-setup-grid,
  .url-source,
  .gutenberg-source {
    grid-template-columns: 1fr;
  }
  .source-actions {
    display: grid;
  }
  .source-actions .btn {
    inline-size: 100%;
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
}
</style>

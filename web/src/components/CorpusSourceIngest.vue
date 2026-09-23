<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { GutenbergHit, PdfAsset } from "../api/pdfCorpus";

const SOURCE_ACCEPT = ".pdf,.txt,.text,.md,.rtf,.doc,.docx,.png,.jpg,.jpeg,.mp3,.wav,.m4a,.ogg,.flac,.webm,.mp4,application/pdf,text/plain";

const props = withDefaults(defineProps<{
  assets?: PdfAsset[];
  assetId?: string;
  illegibility?: number;
  sourceUrl?: string;
  gutenbergQuery?: string;
  hits?: GutenbergHit[];
  selectedAsset?: PdfAsset | null;
  disabled?: boolean;
  busy?: string;
}>(), {
  assets: () => [],
  assetId: "",
  illegibility: 0,
  sourceUrl: "",
  gutenbergQuery: "",
  hits: () => [],
  selectedAsset: null,
  disabled: false,
  busy: "",
});

const emit = defineEmits<{
  "update:assetId": [string];
  "update:illegibility": [number];
  "update:sourceUrl": [string];
  "update:gutenbergQuery": [string];
  useCurrent: [];
  file: [File];
  loadUrl: [];
  searchGutenberg: [];
  importGutenberg: [number];
}>();

const i18n = useI18nStore();
const uploadInput = ref<HTMLInputElement | null>(null);

const illegibilityText = computed(() => i18n.tf(
  "pdf_corpus.source_illegibility_value",
  "{value} out of 100. Higher values OCR more of the source.",
  { value: props.illegibility },
));

function mediaKind(kind?: string) {
  if (!kind) return "";
  return i18n.t(`pdf_corpus.media_kind.${kind}`, kind);
}

function unset() {
  return i18n.t("pdf_corpus.metadata_unset", "Not detected");
}

function formatDate(value?: string | null) {
  if (!value) return unset();
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  } catch {
    return value;
  }
}

function onIllegibility(event: Event) {
  const next = Number((event.target as HTMLInputElement).value);
  emit("update:illegibility", Number.isFinite(next) ? next : 0);
}

function onFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) emit("file", file);
  input.value = "";
}

function importLabel(hit: GutenbergHit) {
  return i18n.tf("pdf_corpus.import_gutenberg_hit", "Load {title} by {author}", {
    title: hit.title,
    author: hit.author || unset(),
  });
}
</script>

<template>
  <div class="source-ingest" :aria-busy="busy ? 'true' : undefined">
    <div class="source-setup-grid">
      <label for="pdf-corpus-source">
        <span>{{ i18n.t("pdf_corpus.source_asset", "Source asset") }}</span>
        <select id="pdf-corpus-source" class="control" :value="assetId" :disabled="disabled" @change="emit('update:assetId', ($event.target as HTMLSelectElement).value)">
          <option value="">{{ i18n.t("pdf_corpus.choose_persisted_pdf", "Choose a saved source…") }}</option>
          <option v-for="asset in assets" :key="asset.asset_id" :value="asset.asset_id">{{ asset.filename }} · {{ asset.page_count }} {{ i18n.t("pdf_corpus.pages", "pages") }} · {{ asset.block_count }} {{ i18n.t("pdf_corpus.blocks", "blocks") }}</option>
        </select>
      </label>
      <div class="ingest-actions">
        <label class="illegibility-field" for="source-illegibility">
          <span>{{ i18n.t("pdf_corpus.source_illegibility", "Source illegibility") }} <b>{{ illegibility }}</b></span>
          <input id="source-illegibility" :value="illegibility" type="range" min="0" max="100" step="1" :disabled="disabled" :aria-valuetext="illegibilityText" aria-describedby="source-illegibility-help" @input="onIllegibility">
          <small id="source-illegibility-help">{{ i18n.t("pdf_corpus.source_illegibility_help", "Set this before choosing a file. Higher values OCR more aggressively when the source is hard to read.") }}</small>
        </label>
        <div class="source-actions">
          <button type="button" class="btn" :disabled="disabled" @click="emit('useCurrent')">{{ i18n.t("pdf_corpus.use_current_pdf", "Use current Explorer PDF") }}</button>
          <button type="button" class="btn source-choose" :disabled="disabled" @click="uploadInput?.click()">{{ busy === "upload" ? i18n.t("pdf_corpus.extracting", "Extracting…") : i18n.t("pdf_corpus.choose_pdf", "Choose source PDF") }}</button>
          <input ref="uploadInput" class="sr-only" tabindex="-1" type="file" :accept="SOURCE_ACCEPT" :aria-label="i18n.t('pdf_corpus.choose_pdf', 'Choose source PDF')" @change="onFile">
        </div>
      </div>
    </div>

    <div class="alternate-sources">
      <form class="url-source" @submit.prevent="emit('loadUrl')">
        <label for="pdf-corpus-source-url">
          <span>{{ i18n.t("pdf_corpus.source_url", "Source URL") }}</span>
          <input id="pdf-corpus-source-url" class="control" type="url" inputmode="url" :value="sourceUrl" :placeholder="i18n.t('pdf_corpus.url_placeholder', 'https://')" :disabled="disabled" @input="emit('update:sourceUrl', ($event.target as HTMLInputElement).value)">
        </label>
        <button type="submit" class="btn" :disabled="disabled || !sourceUrl.trim()">{{ i18n.t("pdf_corpus.load_url", "Load URL") }}</button>
      </form>
      <form class="gutenberg-source" @submit.prevent="emit('searchGutenberg')">
        <label for="pdf-corpus-gutenberg">
          <span>{{ i18n.t("pdf_corpus.gutenberg_search", "Search Project Gutenberg") }}</span>
          <input id="pdf-corpus-gutenberg" class="control" type="search" :value="gutenbergQuery" :placeholder="i18n.t('pdf_corpus.gutenberg_query', 'Title or author')" :disabled="disabled" @input="emit('update:gutenbergQuery', ($event.target as HTMLInputElement).value)">
        </label>
        <button type="submit" class="btn" :disabled="disabled || !gutenbergQuery.trim()">{{ busy === "gutenberg" ? i18n.t("pdf_corpus.extracting", "Extracting…") : i18n.t("pdf_corpus.gutenberg_search", "Search Project Gutenberg") }}</button>
      </form>
      <ul v-if="hits.length" class="gutenberg-hits" :aria-label="i18n.t('pdf_corpus.gutenberg_results', 'Project Gutenberg results')">
        <li v-for="hit in hits" :key="hit.etext_id">
          <button type="button" class="btn" :disabled="disabled" :aria-label="importLabel(hit)" @click="emit('importGutenberg', hit.etext_id)">
            <span>{{ hit.title }}</span>
            <small v-if="hit.author">{{ hit.author }}</small>
          </button>
        </li>
      </ul>
    </div>

    <dl v-if="selectedAsset" class="source-facts">
      <div v-if="selectedAsset.media_kind"><dt>{{ i18n.t("pdf_corpus.media_kind", "Source type") }}</dt><dd>{{ mediaKind(selectedAsset.media_kind) }}</dd></div>
      <div><dt>{{ i18n.t("pdf_corpus.pages", "pages") }}</dt><dd>{{ selectedAsset.page_count }}</dd></div>
      <div><dt>{{ i18n.t("pdf_corpus.blocks", "blocks") }}</dt><dd>{{ selectedAsset.block_count }}</dd></div>
      <div><dt>{{ i18n.t("pdf_corpus.ocr_pages", "OCR page(s)") }}</dt><dd>{{ selectedAsset.ocr_pages }}</dd></div>
      <div><dt>SHA-256</dt><dd>{{ selectedAsset.sha256.slice(0, 16) }}…</dd></div>
      <div><dt>{{ i18n.t("pdf_corpus.loaded", "Loaded") }}</dt><dd>{{ formatDate(selectedAsset.created_at) }}</dd></div>
      <div v-if="selectedAsset.deterministic_checked_at">
        <dt>{{ i18n.t("pdf_corpus.deterministic_check", "Deterministic check") }}</dt>
        <dd>{{ selectedAsset.initial_metadata?.title || unset() }} · {{ selectedAsset.initial_metadata?.document_author || unset() }} · {{ selectedAsset.initial_metadata?.speaker || unset() }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.source-ingest { display: grid; gap: 12px; }
.source-setup-grid { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(240px, 1fr); gap: 12px; align-items: end; }
.source-setup-grid > label, .ingest-actions, .illegibility-field, .url-source label, .gutenberg-source label { display: grid; gap: 5px; }
.ingest-actions { gap: 10px; align-content: end; }
.illegibility-field small { color: var(--muted); line-height: 1.4; }
.illegibility-field input[type="range"] { inline-size: 100%; min-block-size: 24px; }
.source-actions, .alternate-sources { display: grid; gap: 10px; }
.source-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.url-source, .gutenberg-source { display: grid; grid-template-columns: minmax(180px, 1fr) auto; gap: 8px; align-items: end; }
.gutenberg-hits { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; list-style: none; }
.gutenberg-hits .btn { text-align: start; white-space: normal; }
.source-facts { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 0; color: var(--muted); font-size: .8125rem; }
.source-facts div { display: flex; gap: 6px; min-width: 0; }
.source-facts dt { font-weight: 750; }
.source-facts dd { margin: 0; overflow-wrap: anywhere; }
.source-ingest :is(button, input, select) { min-block-size: 24px; }
.source-ingest :is(button, input, select):focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
@media (max-width: 760px) {
  .source-setup-grid, .url-source, .gutenberg-source { grid-template-columns: 1fr; }
  .source-actions { display: grid; }
  .source-actions .btn { inline-size: 100%; }
}
</style>

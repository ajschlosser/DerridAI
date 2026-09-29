<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { corpusBuilderApi, type SourceBlock } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import UiDialog from "../ui/UiDialog.vue";
import UiLoadingState from "../ui/UiLoadingState.vue";

/**
 * Cite evidence that sits outside the record under review: browse the source units around it (the same source,
 * so the citation still resolves to a real, stable block) and tick the ones that support the value.
 */
const props = defineProps<{
  assetId: string;
  /** The record's first block; the window opens around it. */
  aroundBlockId: string;
  /** The record's own blocks, marked so they are not mistaken for outside evidence. */
  recordBlockIds: string[];
  fieldLabel: string;
  busy?: boolean;
  /** Spans already cited from other records, ticked on open so confirming can also remove them. */
  initialChosen?: string[];
}>();
const emit = defineEmits<{ close: []; confirm: [blockIds: string[]] }>();
const i18n = useI18nStore();
const PAGE = 60;
const blocks = ref<SourceBlock[]>([]);
const offset = ref(0);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const query = ref("");
const chosen = ref<string[]>([...(props.initialChosen || []).map(String)]);
const own = computed(() => new Set(props.recordBlockIds.map(String)));

const shown = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  return blocks.value.filter(
    (block) =>
      !needle ||
      String(block.text || "")
        .toLocaleLowerCase()
        .includes(needle),
  );
});
const canEarlier = computed(() => offset.value > 0);
const canLater = computed(() => offset.value + blocks.value.length < total.value);

async function load(start: number) {
  loading.value = true;
  error.value = "";
  try {
    const result = await corpusBuilderApi.blocks(props.assetId, Math.max(0, start), PAGE);
    blocks.value = result.items;
    total.value = result.total;
    offset.value = Math.max(0, start);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}
onMounted(async () => {
  loading.value = true;
  try {
    const result = await corpusBuilderApi.blocksAround(props.assetId, props.aroundBlockId, PAGE);
    blocks.value = result.items;
    total.value = result.total;
    offset.value = result.offset;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
});
function toggle(id: string) {
  chosen.value = chosen.value.includes(id)
    ? chosen.value.filter((item) => item !== id)
    : [...chosen.value, id];
}
function locator(block: SourceBlock) {
  return block.page != null ? `${i18n.t("pdf_corpus.page_abbrev")} ${block.page}` : block.block_id;
}
</script>

<template>
  <UiDialog
    :open="true"
    size="xlarge"
    :title="i18n.tf('pdf_corpus.evidence_browser_title', { field: fieldLabel })"
    :description="i18n.t('pdf_corpus.evidence_browser_help')"
    :close-label="i18n.t('ui.close')"
    @close="emit('close')"
  >
    <div class="browser-tools">
      <input
        v-model="query"
        type="search"
        class="control"
        :aria-label="i18n.t('pdf_corpus.evidence_filter')"
        :placeholder="i18n.t('pdf_corpus.evidence_filter')"
      />
      <button
        type="button"
        class="btn small"
        :disabled="!canEarlier || loading"
        @click="load(offset - PAGE)"
      >
        {{ i18n.t("pdf_corpus.evidence_browser_earlier") }}
      </button>
      <button
        type="button"
        class="btn small"
        :disabled="!canLater || loading"
        @click="load(offset + PAGE)"
      >
        {{ i18n.t("pdf_corpus.evidence_browser_later") }}
      </button>
    </div>
    <p v-if="error" class="browser-error" role="alert">{{ error }}</p>
    <UiLoadingState v-else-if="loading" :label="i18n.t('pdf_corpus.units_loading')" />
    <ol v-else class="browser-list">
      <li
        v-for="block in shown"
        :key="block.block_id"
        :data-chosen="chosen.includes(block.block_id) ? 'true' : undefined"
        :data-own="own.has(block.block_id) ? 'true' : undefined"
      >
        <label>
          <input
            type="checkbox"
            :checked="chosen.includes(block.block_id)"
            :disabled="own.has(block.block_id)"
            @change="toggle(block.block_id)"
          />
          <span class="browser-locator">{{ locator(block) }}</span>
          <span v-if="own.has(block.block_id)" class="browser-own">{{
            i18n.t("pdf_corpus.evidence_browser_this_record")
          }}</span>
          <span class="browser-text">{{ block.text }}</span>
        </label>
      </li>
      <li v-if="!shown.length" class="browser-status" role="status">
        {{ i18n.t("pdf_corpus.evidence_no_match") }}
      </li>
    </ol>
    <template #footer>
      <span class="browser-count" role="status">{{
        i18n.tf("pdf_corpus.evidence_browser_chosen", { count: chosen.length })
      }}</span>
      <button type="button" class="btn" @click="emit('close')">{{ i18n.t("ui.cancel") }}</button>
      <button
        type="button"
        class="btn primary"
        :disabled="(!chosen.length && !initialChosen?.length) || busy"
        @click="emit('confirm', chosen)"
      >
        {{ i18n.t("pdf_corpus.evidence_browser_confirm") }}
      </button>
    </template>
  </UiDialog>
</template>

<style scoped>
.browser-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  align-items: center;
  margin-block-end: var(--space-3, 12px);
}
.browser-tools .control {
  flex: 1;
  min-inline-size: 12rem;
}
.browser-list {
  display: grid;
  gap: var(--space-2, 8px);
  margin: 0;
  padding: 0;
  list-style: none;
}
.browser-list li {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.browser-list li[data-chosen="true"] {
  border-color: var(--ui-accent, var(--accent));
  background: var(--surface-selected);
}
.browser-list li[data-own="true"] {
  opacity: 0.75;
}
.browser-list label {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 4px 10px;
  align-items: baseline;
  padding: 8px 10px;
  cursor: pointer;
}
.browser-locator {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}
.browser-own {
  grid-column: 3;
  color: var(--tone-info-fg);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
}
.browser-text {
  grid-column: 2 / -1;
  font-family: var(--font-reading, Georgia, serif);
  overflow-wrap: anywhere;
}
.browser-status,
.browser-error,
.browser-count {
  color: var(--text-secondary);
  font-size: var(--fs-base);
}
.browser-error {
  color: var(--tone-danger-fg);
}
</style>

<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { corpusBuilderApi, type RecordContext, type RecordContextItem } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    buildId: string;
    recordId: string;
    text: string;
    showContext?: boolean;
  }>(),
  { showContext: true },
);
const emit = defineEmits<{ select: [recordId: string] }>();
const i18n = useI18nStore();
const window_ = ref<HTMLElement | null>(null);
const context = ref<RecordContext | null>(null);
const failed = ref(false);
const expanded = ref<Set<string>>(new Set());
const cache = new Map<string, RecordContext>();
let ticket = 0;

const enabled = computed(() => props.showContext);
const visible = computed(() => ({
  before: (context.value?.before ?? []).slice(-3),
  after: (context.value?.after ?? []).slice(0, 3),
}));

function preview(item: RecordContextItem) {
  const text = String(item.text || "")
    .replace(/\s+/g, " ")
    .trim();
  if (expanded.value.has(item.record_id) || text.length <= 150) return text;
  return `${text.slice(0, 150).trimEnd()}…`;
}
function toggleExpanded(recordId: string) {
  const next = new Set(expanded.value);
  if (next.has(recordId)) next.delete(recordId);
  else next.add(recordId);
  expanded.value = next;
}
function pages(item: RecordContextItem) {
  if (item.page_start == null) return "";
  return item.page_end != null && item.page_end !== item.page_start
    ? `${item.page_start}–${item.page_end}`
    : String(item.page_start);
}
function load() {
  context.value = null;
  failed.value = false;
  expanded.value = new Set();
  if (!enabled.value || !props.buildId || !props.recordId) return;
  const key = `${props.buildId}:${props.recordId}`;
  const mine = ++ticket;
  void (async () => {
    try {
      const raw =
        cache.get(key) ?? (await corpusBuilderApi.recordContext(props.buildId, props.recordId));
      const result: RecordContext = {
        ...raw,
        before: Array.isArray(raw?.before) ? raw.before : [],
        after: Array.isArray(raw?.after) ? raw.after : [],
      };
      cache.set(key, result);
      if (mine === ticket) context.value = result;
    } catch {
      if (mine === ticket) failed.value = true;
    }
  })();
}

watch(() => [props.buildId, props.recordId, enabled.value], load, { immediate: true });
onMounted(() => window_.value?.focus({ preventScroll: true }));
onBeforeUnmount(() => {
  ticket += 1;
});
</script>

<template>
  <div
    ref="window_"
    class="context-reader"
    :class="{ 'is-plain': !context }"
    role="region"
    tabindex="0"
    :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
  >
    <ol
      v-if="visible.before.length"
      class="ctx-list"
      :aria-label="i18n.t('pdf_corpus.context_before')"
    >
      <li v-for="item in visible.before" :key="item.record_id" class="ctx-item">
        <button type="button" class="ctx-jump" @click="emit('select', item.record_id)">
          <span>{{ item.record_id }}</span>
          <span v-if="pages(item)">{{ i18n.t("pdf_corpus.page_abbrev") }} {{ pages(item) }}</span>
        </button>
        <p>
          {{ preview(item) }}
          <button
            v-if="String(item.text || '').trim().length > 150"
            type="button"
            class="ctx-expand"
            :aria-expanded="expanded.has(item.record_id)"
            @click.stop="toggleExpanded(item.record_id)"
          >
            {{ expanded.has(item.record_id) ? i18n.t("ui.collapse") : "…" }}
          </button>
        </p>
      </li>
    </ol>
    <div class="ctx-focus" data-record-text :aria-label="i18n.t('pdf_corpus.reviewed_record_text')">
      {{ text }}
    </div>
    <ol
      v-if="visible.after.length"
      class="ctx-list"
      :aria-label="i18n.t('pdf_corpus.context_after')"
    >
      <li v-for="item in visible.after" :key="item.record_id" class="ctx-item">
        <button type="button" class="ctx-jump" @click="emit('select', item.record_id)">
          <span>{{ item.record_id }}</span>
          <span v-if="pages(item)">{{ i18n.t("pdf_corpus.page_abbrev") }} {{ pages(item) }}</span>
        </button>
        <p>
          {{ preview(item) }}
          <button
            v-if="String(item.text || '').trim().length > 150"
            type="button"
            class="ctx-expand"
            :aria-expanded="expanded.has(item.record_id)"
            @click.stop="toggleExpanded(item.record_id)"
          >
            {{ expanded.has(item.record_id) ? i18n.t("ui.collapse") : "…" }}
          </button>
        </p>
      </li>
    </ol>
    <p v-if="failed" class="ctx-note" role="status">
      {{ i18n.t("pdf_corpus.context_unavailable") }}
    </p>
  </div>
</template>

<style scoped>
.context-reader {
  display: grid;
  gap: 14px;
  padding: 14px 24px 20px;
  min-block-size: 220px;
  max-block-size: max(220px, calc(100vh - 320px));
  overflow-y: auto;
  overscroll-behavior: contain;
}
.context-reader.is-plain {
  align-content: start;
}
.ctx-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ctx-item {
  display: grid;
  gap: 2px;
  padding-inline-start: 12px;
  border-inline-start: 2px solid var(--border-subtle);
  font-size: 0.9375rem;
  line-height: 1.6;
}
.ctx-item p {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ctx-jump {
  display: flex;
  gap: 10px;
  padding: 0;
  border: 0;
  color: var(--text-tertiary);
  background: none;
  font: inherit;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  cursor: pointer;
  text-align: start;
}
.ctx-jump:hover,
.ctx-expand:hover {
  color: var(--accent-fg);
  text-decoration: underline;
}
.ctx-jump:focus-visible,
.ctx-expand:focus-visible {
  outline: var(--focus-ring-width) solid var(--ui-accent, var(--accent));
  outline-offset: var(--focus-ring-offset);
}
.ctx-expand {
  padding: 0 0.2rem;
  border: 0;
  color: var(--accent-fg);
  background: none;
  font: inherit;
  cursor: pointer;
}
.ctx-focus {
  padding: 16px 18px;
  border-inline-start: 4px solid var(--ui-accent, var(--accent));
  border-radius: var(--radius-control);
  background: var(--surface-selected);
  box-shadow: var(--shadow-card);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ctx-note {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
</style>

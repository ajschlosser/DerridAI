<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { corpusBuilderApi, type RecordContext, type RecordContextItem } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { realtime } from "../../realtime";
import { dataTopic } from "../../realtime/resourceKeys";

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
const cache = new Map<string, { context: RecordContext; text: string }>();
let ticket = 0;

const enabled = computed(() => props.showContext);
const visible = computed(() => ({
  before: (context.value?.before ?? []).slice(-3),
  after: (context.value?.after ?? []).slice(0, 3),
}));

function preview(item: RecordContextItem) {
  const text = String(item.text || "");
  if (expanded.value.has(item.record_id) || text.length <= 150) return text;
  return `${text.slice(0, 150)}…`;
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
  const mine = ++ticket;
  context.value = null;
  failed.value = false;
  expanded.value = new Set();
  if (!enabled.value || !props.buildId || !props.recordId) return;
  const key = `${props.buildId}:${props.recordId}`;
  const buildId = props.buildId;
  const recordId = props.recordId;
  const text = props.text;
  void (async () => {
    try {
      const cached = cache.get(key);
      const raw =
        cached?.text === text
          ? cached.context
          : await corpusBuilderApi.recordContext(buildId, recordId);
      const result: RecordContext = {
        ...raw,
        before: Array.isArray(raw?.before) ? raw.before : [],
        after: Array.isArray(raw?.after) ? raw.after : [],
      };
      if (mine !== ticket) return;
      cache.delete(key);
      cache.set(key, { context: result, text });
      while (cache.size > 24) {
        const oldest = cache.keys().next().value;
        if (oldest === undefined) break;
        cache.delete(oldest);
      }
      context.value = result;
    } catch {
      if (mine === ticket) failed.value = true;
    }
  })();
}

watch(() => [props.buildId, props.recordId, props.text, enabled.value], load, { immediate: true });
const stopFollowing = realtime.subscribe(dataTopic("corpus_records"), () => {
  cache.clear();
  load();
});
onBeforeUnmount(() => {
  ticket += 1;
  stopFollowing();
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
            :aria-label="
              expanded.has(item.record_id)
                ? i18n.t('pdf_corpus.context_collapse')
                : i18n.t('pdf_corpus.context_expand')
            "
            @click.stop="toggleExpanded(item.record_id)"
          >
            {{
              expanded.has(item.record_id)
                ? i18n.t("ui.collapse")
                : i18n.t("pdf_corpus.context_expand")
            }}
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
            :aria-label="
              expanded.has(item.record_id)
                ? i18n.t('pdf_corpus.context_collapse')
                : i18n.t('pdf_corpus.context_expand')
            "
            @click.stop="toggleExpanded(item.record_id)"
          >
            {{
              expanded.has(item.record_id)
                ? i18n.t("ui.collapse")
                : i18n.t("pdf_corpus.context_expand")
            }}
          </button>
        </p>
      </li>
    </ol>
    <p v-if="failed" class="ctx-note" role="status">
      {{ i18n.t("pdf_corpus.context_unavailable") }}
      <button type="button" class="ctx-expand" @click="load">{{ i18n.t("ui.retry") }}</button>
    </p>
  </div>
</template>

<style scoped>
.context-reader {
  display: grid;
  gap: 14px;
  padding: 14px 24px 20px;
  min-block-size: 220px;
  overflow-wrap: anywhere;
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

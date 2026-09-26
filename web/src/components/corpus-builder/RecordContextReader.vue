<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { corpusBuilderApi, type RecordContext, type RecordContextItem } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";

/**
 * The record under review, centred in a reading window with the records around it above and below.
 * Neighbours fade with distance so the reviewer sees full context (short records, sentence-level
 * units) without losing which text is under review. The window is scrollable: neighbours fill
 * whatever room the focus record leaves, and more can be scrolled into view.
 */
const props = withDefaults(
  defineProps<{
    buildId: string;
    recordId: string;
    text: string;
    /** Turn the surrounding records off (a reviewer preference). */
    showContext?: boolean;
  }>(),
  { showContext: true },
);
const emit = defineEmits<{ select: [recordId: string] }>();
const i18n = useI18nStore();

const window_ = ref<HTMLElement | null>(null);
const focus = ref<HTMLElement | null>(null);
const context = ref<RecordContext | null>(null);
const failed = ref(false);
const cache = new Map<string, RecordContext>();
let ticket = 0;

const enabled = computed(() => props.showContext);

async function load() {
  context.value = null;
  failed.value = false;
  if (!enabled.value || !props.buildId || !props.recordId) return;
  const key = `${props.buildId}:${props.recordId}`;
  const mine = ++ticket;
  try {
    const result =
      cache.get(key) ?? (await corpusBuilderApi.recordContext(props.buildId, props.recordId));
    cache.set(key, result);
    if (mine !== ticket) return;
    context.value = result;
    await nextTick();
    centre();
  } catch {
    // Context is a convenience; the record itself is unaffected.
    if (mine === ticket) failed.value = true;
  }
}

/** Put the focus record in the middle of the window (or at its top when it is taller). */
function centre() {
  const box = window_.value;
  const focused = focus.value;
  if (!box || !focused) return;
  const spare = box.clientHeight - focused.offsetHeight;
  box.scrollTop = Math.max(0, focused.offsetTop - box.offsetTop - (spare > 0 ? spare / 2 : 12));
}

// Fade: the nearest neighbour is clearly readable, distant ones recede.
function opacity(distance: number) {
  return Math.max(0.28, 0.78 - 0.09 * (distance - 1));
}
function pages(item: RecordContextItem) {
  if (item.page_start == null) return "";
  return item.page_end != null && item.page_end !== item.page_start
    ? `${item.page_start}–${item.page_end}`
    : String(item.page_start);
}

watch(() => [props.buildId, props.recordId, enabled.value], load, { immediate: true });
watch(
  () => props.text,
  () => nextTick(centre),
);
onBeforeUnmount(() => {
  ticket += 1;
});
</script>

<template>
  <div ref="window_" class="context-reader" :class="{ 'is-plain': !context }">
    <ol
      v-if="context?.before.length"
      class="ctx-list"
      :aria-label="i18n.t('pdf_corpus.context_before')"
    >
      <li
        v-for="(item, index) in context.before"
        :key="item.record_id"
        class="ctx-item"
        :style="{ opacity: opacity(context.before.length - index) }"
      >
        <button type="button" class="ctx-jump" @click="emit('select', item.record_id)">
          <span>{{ item.record_id }}</span>
          <span v-if="pages(item)">{{ i18n.t("pdf_corpus.page_abbrev") }} {{ pages(item) }}</span>
        </button>
        <p>{{ item.text }}</p>
      </li>
    </ol>
    <div ref="focus" class="ctx-focus" :aria-label="i18n.t('pdf_corpus.reviewed_record_text')">
      {{ text }}
    </div>
    <ol
      v-if="context?.after.length"
      class="ctx-list"
      :aria-label="i18n.t('pdf_corpus.context_after')"
    >
      <li
        v-for="(item, index) in context.after"
        :key="item.record_id"
        class="ctx-item"
        :style="{ opacity: opacity(index + 1) }"
      >
        <button type="button" class="ctx-jump" @click="emit('select', item.record_id)">
          <span>{{ item.record_id }}</span>
          <span v-if="pages(item)">{{ i18n.t("pdf_corpus.page_abbrev") }} {{ pages(item) }}</span>
        </button>
        <p>{{ item.text }}</p>
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
  max-block-size: min(62vh, 640px);
  overflow-y: auto;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
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
  transition: opacity var(--motion-base) var(--ease-standard);
}
.ctx-item:hover,
.ctx-item:focus-within {
  opacity: 1 !important;
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
.ctx-jump:hover {
  color: var(--accent-fg);
  text-decoration: underline;
}
.ctx-jump:focus-visible {
  outline: var(--focus-ring-width) solid var(--ui-accent, var(--accent));
  outline-offset: var(--focus-ring-offset);
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
@media (prefers-reduced-motion: reduce) {
  .context-reader {
    scroll-behavior: auto;
  }
  .ctx-item {
    transition: none;
  }
}
</style>

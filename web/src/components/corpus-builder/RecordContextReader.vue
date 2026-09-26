<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { corpusBuilderApi, type RecordContext, type RecordContextItem } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { fitContext } from "../../features/corpus-builder/domain/contextWindow";

/**
 * The record under review, centred in a reading window with the records around it above and below.
 * Neighbours fade with distance so the reviewer sees full context (short records, sentence-level
 * units) without losing which text is under review. The window is scrollable: neighbours fill
 * whatever room the focus record leaves: a long record has few or no neighbours so it stays in the reader's line
 * of sight, a short one has many. The window is scrollable and the record is centred in it.
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

// The window's capacity in characters, from its size and type; unmeasured (0) falls back to a modest default.
const capacity = ref(0);
const DEFAULT_CAPACITY = 2400;
/**
 * Estimate how many characters fit the window: its usable height in lines times its width in characters, from the
 * computed font size (a line is ~1.65em tall, an average glyph ~0.52em wide). It is deliberately approximate: it only
 * decides how many neighbours to offer (see fitContext); the record is centred by real layout afterwards.
 */
function measure() {
  const box = window_.value;
  if (!box || !box.clientWidth) return;
  const style = getComputedStyle(box);
  const size = parseFloat(style.fontSize) || 16;
  const maxHeight = parseFloat(style.maxHeight) || window.innerHeight * 0.62;
  const width = box.clientWidth - (parseFloat(style.paddingInline) || 48);
  const lines = maxHeight / (size * 1.65);
  capacity.value = Math.max(0, Math.floor(lines * (width / (size * 0.52))));
}
const visible = computed(() => {
  const before = context.value?.before ?? [];
  const after = context.value?.after ?? [];
  const cap = capacity.value || DEFAULT_CAPACITY;
  // The focus block's padding and each neighbour's heading cost about a line and a half of text each.
  const line = Math.max(20, Math.floor(cap / 24));
  return fitContext(before, after, props.text.length + line * 2, cap, { overhead: line * 1.5 });
});

async function load() {
  context.value = null;
  failed.value = false;
  if (!enabled.value || !props.buildId || !props.recordId) return;
  const key = `${props.buildId}:${props.recordId}`;
  const mine = ++ticket;
  try {
    const raw =
      cache.get(key) ?? (await corpusBuilderApi.recordContext(props.buildId, props.recordId));
    // A malformed or older response must never take the record's own text down with it.
    const result: RecordContext = {
      ...raw,
      before: Array.isArray(raw?.before) ? raw.before : [],
      after: Array.isArray(raw?.after) ? raw.after : [],
    };
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
let observer: ResizeObserver | null = null;
let lastWidth = 0;
onMounted(() => {
  measure();
  if (typeof ResizeObserver === "undefined" || !window_.value) return;
  // Only a change of width re-fits: the window's own height follows its content, so watching it would loop.
  observer = new ResizeObserver(() => {
    const width = window_.value?.clientWidth ?? 0;
    if (width === lastWidth) return;
    lastWidth = width;
    measure();
    void nextTick(centre);
  });
  observer.observe(window_.value);
});
watch(capacity, () => nextTick(centre));
onBeforeUnmount(() => {
  ticket += 1;
  observer?.disconnect();
});
</script>

<template>
  <!-- Scrollable, so it must be keyboard-focusable (WCAG 2.1.1) and named as a region. -->
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
      <li
        v-for="(item, index) in visible.before"
        :key="item.record_id"
        class="ctx-item"
        :style="{ opacity: opacity(visible.before.length - index) }"
      >
        <button type="button" class="ctx-jump" @click="emit('select', item.record_id)">
          <span>{{ item.record_id }}</span>
          <span v-if="pages(item)">{{ i18n.t("pdf_corpus.page_abbrev") }} {{ pages(item) }}</span>
        </button>
        <p>{{ item.text }}</p>
      </li>
    </ol>
    <div
      ref="focus"
      class="ctx-focus"
      data-record-text
      :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
    >
      {{ text }}
    </div>
    <ol
      v-if="visible.after.length"
      class="ctx-list"
      :aria-label="i18n.t('pdf_corpus.context_after')"
    >
      <li
        v-for="(item, index) in visible.after"
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

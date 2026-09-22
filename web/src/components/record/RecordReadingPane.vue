<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { RecordAnnotationItem } from "../../types/record";

const props = withDefaults(
  defineProps<{
    text: string;
    findQuery?: string;
    wordCount?: number;
    characterCount?: number;
    annotations?: RecordAnnotationItem[];
    canAnnotate?: boolean;
    summaryMode?: boolean;
  }>(),
  {
    findQuery: "",
    wordCount: 0,
    characterCount: 0,
    annotations: () => [],
    canAnnotate: false,
    summaryMode: false,
  },
);
const emit = defineEmits<{
  find: [value: string];
  annotate: [selection: { field: string; quote: string }];
}>();
const i18n = useI18nStore();
const root = ref<HTMLElement | null>(null);
const search = ref(props.findQuery || "");
const focusMode = ref(false);
const selectedQuote = ref("");
const selectionStyle = ref<Record<string, string>>({});
const tooltipId = `annotation-tooltip-${useId()}`;
const tooltipAnnotations = ref<RecordAnnotationItem[]>([]);
const tooltipStyle = ref<Record<string, string>>({});
const tooltipOpen = ref(false);

interface MarkedSegment {
  text: string;
  search: boolean;
  annotations: RecordAnnotationItem[];
  annotation: boolean;
}
interface Interval {
  start: number;
  end: number;
  kind: "search" | "annotation";
  annotation?: RecordAnnotationItem;
}
const segments = computed<MarkedSegment[]>(() => {
  const text = String(props.text || "");
  if (!text) return [];
  const intervals: Interval[] = [];
  const lower = text.toLocaleLowerCase();
  const query = search.value.trim().toLocaleLowerCase();
  if (query) {
    let at = 0;
    while ((at = lower.indexOf(query, at)) >= 0) {
      intervals.push({ start: at, end: at + query.length, kind: "search" });
      at += Math.max(1, query.length);
    }
  }
  for (const annotation of props.annotations || []) {
    const quote = String(annotation.quote || "").trim();
    if (!quote) continue;
    const needle = quote.toLocaleLowerCase();
    let at = 0;
    // Highlight every exact occurrence. This is more predictable than binding an
    // annotation to the first match when repeated quotations appear in a record.
    while ((at = lower.indexOf(needle, at)) >= 0) {
      intervals.push({ start: at, end: at + quote.length, kind: "annotation", annotation });
      at += Math.max(1, quote.length);
    }
  }
  if (!intervals.length) return [{ text, search: false, annotations: [], annotation: false }];
  const bounds = new Set<number>([0, text.length]);
  for (const item of intervals) {
    bounds.add(item.start);
    bounds.add(item.end);
  }
  const points = [...bounds].sort((a, b) => a - b);
  const out: MarkedSegment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const start = points[i],
      end = points[i + 1];
    if (end <= start) continue;
    const hits = intervals.filter((item) => item.start < end && item.end > start);
    const annotations = [
      ...new Map(
        hits
          .filter((item) => item.kind === "annotation" && item.annotation)
          .map((item) => [item.annotation!.id, item.annotation!]),
      ).values(),
    ];
    out.push({
      text: text.slice(start, end),
      search: hits.some((item) => item.kind === "search"),
      annotations,
      annotation: annotations.length > 0,
    });
  }
  return out;
});
const matchCount = computed(() => {
  const q = search.value.trim().toLocaleLowerCase();
  if (!q) return 0;
  let at = 0,
    count = 0;
  const hay = String(props.text || "").toLocaleLowerCase();
  while ((at = hay.indexOf(q, at)) >= 0) {
    count++;
    at += Math.max(1, q.length);
  }
  return count;
});
function onFind(value: string) {
  search.value = value;
  emit("find", value);
}
function clearFind() {
  onFind("");
  void nextTick(() =>
    root.value?.querySelector<HTMLInputElement>(".record-reading-search input")?.focus(),
  );
}
function captureSelection() {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount || !root.value) return;
  const range = selection.getRangeAt(0);
  const node =
    range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
      ? range.commonAncestorContainer
      : range.commonAncestorContainer.parentElement;
  if (!node || !root.value.contains(node)) return;
  const quote = String(selection.toString() || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!quote) return;
  const rect = range.getBoundingClientRect();
  selectedQuote.value = quote;
  selectionStyle.value = {
    left: `${Math.max(12, Math.min(window.innerWidth - 250, (rect.left + rect.right) / 2 - 125))}px`,
    top: `${Math.max(12, rect.top - 52)}px`,
  };
}
async function copySelection() {
  if (!selectedQuote.value) return;
  try {
    await navigator.clipboard.writeText(selectedQuote.value);
  } catch {
    // Clipboard access can be unavailable in embedded or restricted browser contexts.
  }
  selectedQuote.value = "";
}
function annotate() {
  if (!selectedQuote.value) return;
  emit("annotate", { field: "text", quote: selectedQuote.value });
  selectedQuote.value = "";
}
function closeSelection() {
  selectedQuote.value = "";
  window.getSelection()?.removeAllRanges();
}
function formatDate(value?: string | null) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat(i18n.locale, { dateStyle: "medium", timeStyle: "short" }).format(
      new Date(value),
    );
  } catch {
    return String(value);
  }
}
function showAnnotationTooltip(
  event: MouseEvent | FocusEvent,
  annotations: RecordAnnotationItem[],
) {
  if (!annotations.length) return;
  const target = event.currentTarget as HTMLElement | null;
  if (!target) return;
  const rect = target.getBoundingClientRect();
  const width = Math.min(390, window.innerWidth - 24);
  const left = Math.max(12, Math.min(window.innerWidth - width - 12, rect.left));
  const top =
    rect.bottom + 10 + 220 < window.innerHeight ? rect.bottom + 8 : Math.max(12, rect.top - 230);
  tooltipAnnotations.value = annotations;
  tooltipStyle.value = { left: `${left}px`, top: `${top}px`, width: `${width}px` };
  tooltipOpen.value = true;
}
function hideAnnotationTooltip() {
  tooltipOpen.value = false;
  tooltipAnnotations.value = [];
}
function onGlobalKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (selectedQuote.value) {
    event.preventDefault();
    closeSelection();
  }
  if (tooltipOpen.value) hideAnnotationTooltip();
}
onMounted(() => window.addEventListener("keydown", onGlobalKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onGlobalKeydown));
</script>

<template>
  <article
    ref="root"
    class="record-reading-pane"
    :class="{ 'focus-mode': focusMode }"
    @mouseup="captureSelection"
    @keyup="captureSelection"
  >
    <header class="record-reading-toolbar">
      <div>
        <p>
          {{
            props.summaryMode
              ? i18n.t("record.researcher_summary", "Researcher summary")
              : i18n.t("record.extracted_text", "Extracted text")
          }}
        </p>
        <span
          >{{ props.wordCount.toLocaleString(i18n.locale) }} {{ i18n.t("record.words", "words") }} ·
          {{ props.characterCount.toLocaleString(i18n.locale) }}
          {{ i18n.t("record.characters", "characters")
          }}<template v-if="search">
            · {{ matchCount }} {{ i18n.t("record.matches", "matches") }}</template
          ></span
        >
      </div>
      <div class="record-reading-controls">
        <label class="record-reading-search"
          ><span class="sr-only">{{ i18n.t("record.find_text", "Find in record text") }}</span
          ><AppIcon name="search" /><input
            :value="search"
            :placeholder="i18n.t('record.find_text', 'Find in record text')"
            :aria-label="i18n.t('record.find_text', 'Find in record text')"
            @input="onFind(($event.target as HTMLInputElement).value)"
          /><button
            v-if="search"
            type="button"
            :aria-label="i18n.t('record.clear_find', 'Clear find query')"
            @click="clearFind"
          >
            ×
          </button></label
        >
        <button
          type="button"
          class="focus-button"
          :aria-pressed="focusMode"
          @click="focusMode = !focusMode"
        >
          {{
            focusMode
              ? i18n.t("record.exit_focus", "Exit focus")
              : i18n.t("record.focus_mode", "Focus mode")
          }}
        </button>
      </div>
    </header>
    <div
      class="record-reading-text"
      tabindex="0"
      :aria-label="i18n.t('record.text', 'Record text')"
    >
      <template v-for="(segment, index) in segments" :key="index">
        <mark
          v-if="segment.search"
          class="search-hit"
          :class="{ 'annotation-hit': segment.annotation }"
          :tabindex="segment.annotation ? 0 : undefined"
          :aria-describedby="segment.annotation && tooltipOpen ? tooltipId : undefined"
          @mouseenter="segment.annotation && showAnnotationTooltip($event, segment.annotations)"
          @mouseleave="segment.annotation && hideAnnotationTooltip()"
          @focus="segment.annotation && showAnnotationTooltip($event, segment.annotations)"
          @blur="segment.annotation && hideAnnotationTooltip()"
          >{{ segment.text }}</mark
        >
        <mark
          v-else-if="segment.annotation"
          class="annotation-hit"
          tabindex="0"
          :aria-describedby="tooltipOpen ? tooltipId : undefined"
          @mouseenter="showAnnotationTooltip($event, segment.annotations)"
          @mouseleave="hideAnnotationTooltip"
          @focus="showAnnotationTooltip($event, segment.annotations)"
          @blur="hideAnnotationTooltip"
          >{{ segment.text }}</mark
        >
        <span v-else>{{ segment.text }}</span>
      </template>
    </div>
    <teleport to="body">
      <div
        v-if="selectedQuote"
        class="record-selection-popover"
        :style="selectionStyle"
        role="toolbar"
        :aria-label="i18n.t('record.selection_actions', 'Selected text actions')"
      >
        <span>{{
          selectedQuote.length > 42 ? selectedQuote.slice(0, 42) + "…" : selectedQuote
        }}</span>
        <button type="button" @click="copySelection">
          <AppIcon name="copy" />{{ i18n.t("ui.copy", "Copy") }}
        </button>
        <button v-if="props.canAnnotate" type="button" class="primary" @click="annotate">
          <AppIcon name="plus" />{{ i18n.t("annotations.add_note_tags", "Add note / tags") }}
        </button>
      </div>
      <aside
        v-if="tooltipOpen && tooltipAnnotations.length"
        :id="tooltipId"
        class="record-annotation-tooltip"
        :style="tooltipStyle"
        role="tooltip"
      >
        <div class="record-annotation-tooltip-head">
          <AppIcon name="edit" /><strong>{{
            tooltipAnnotations.length === 1
              ? i18n.t("annotations.annotation", "Annotation")
              : i18n.tf("annotations.annotation_count", "{count} annotations", {
                  count: tooltipAnnotations.length,
                })
          }}</strong>
        </div>
        <article v-for="annotation in tooltipAnnotations" :key="annotation.id">
          <p v-if="annotation.note">{{ annotation.note }}</p>
          <p v-else class="annotation-no-note">{{ i18n.t("annotations.no_note", "No note") }}</p>
          <div v-if="annotation.tags?.length" class="annotation-tooltip-tags">
            <span v-for="tag in annotation.tags" :key="tag">{{ tag }}</span>
          </div>
          <small
            ><b>{{ annotation.author }}</b
            ><template v-if="annotation.created_at">
              · {{ formatDate(annotation.created_at) }}</template
            ></small
          >
        </article>
      </aside>
    </teleport>
  </article>
</template>

<style scoped>
.record-reading-pane {
  min-width: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}
.record-reading-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-raised);
}
.record-reading-toolbar p {
  margin: 0;
  color: var(--text);
  font-size: 0.84375rem;
  font-weight: 800;
}
.record-reading-toolbar span {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.record-reading-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
.record-reading-search {
  min-width: 220px;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  padding: 0 8px;
  color: var(--muted);
}
.record-reading-search :deep(svg) {
  width: 15px;
  height: 15px;
}
.record-reading-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 0.8125rem;
}
.record-reading-search button {
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.focus-button {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  padding: 0 10px;
  color: var(--text-2);
  font-weight: 700;
  cursor: pointer;
}
.record-reading-text {
  max-width: 82ch;
  margin: 0 auto;
  padding: clamp(26px, 4vw, 54px) clamp(24px, 5vw, 70px);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--text);
  font:
    15.5px/1.82 Georgia,
    "Times New Roman",
    serif;
  outline: none;
}
.record-reading-text:focus-visible {
  box-shadow: inset 0 0 0 var(--focus-ring-width) var(--focus-ring-soft);
}
mark {
  color: inherit;
}
.search-hit {
  background: var(--mark-bg);
  color: var(--mark-fg);
  border-radius: 2px;
  padding: 0 1px;
}
.annotation-hit {
  color: var(--text);
  background: color-mix(in srgb, var(--ui-accent-soft, #eaf6ee) 74%, var(--tone-warn-bg));
  border-bottom: 2px solid
    color-mix(in srgb, var(--ui-accent, #3c8d62) 70%, var(--tone-warn-border));
  cursor: help;
}
.annotation-hit:focus-visible {
  outline: 3px solid var(--ui-accent-focus, #9fc8ad);
  outline-offset: 2px;
  border-radius: 2px;
}
.focus-mode {
  position: fixed;
  inset: 74px 32px 28px max(32px, var(--sidebar-width, 250px));
  z-index: 70;
  overflow: auto;
  box-shadow: var(--shadow-overlay);
}
.focus-mode .record-reading-toolbar {
  position: sticky;
  top: 0;
  z-index: 2;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.record-selection-popover {
  position: fixed;
  z-index: 10020;
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: calc(100vw - 24px);
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
  font-size: 0.8125rem;
}
.record-selection-popover > span {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
}
.record-selection-popover button {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 5px;
  border: 0;
  border-radius: 7px;
  background: var(--soft);
  padding: 0 8px;
  color: var(--text-2);
  font-weight: 700;
  cursor: pointer;
}
.record-selection-popover button.primary {
  background: var(--ui-accent, #3c8d62);
  color: var(--accent-on);
}
.record-selection-popover :deep(svg) {
  width: 14px;
  height: 14px;
}
.record-annotation-tooltip {
  position: fixed;
  z-index: 10040;
  max-height: min(320px, calc(100vh - 24px));
  overflow: auto;
  padding: 11px;
  border: 1px solid var(--line);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
  color: var(--text-2);
  font:
    12px/1.45 system-ui,
    sans-serif;
  pointer-events: none;
}
.record-annotation-tooltip-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-bottom: 7px;
  border-bottom: 1px solid var(--line);
  color: var(--text-2);
}
.record-annotation-tooltip-head :deep(svg) {
  width: 15px;
  height: 15px;
}
.record-annotation-tooltip article {
  display: grid;
  gap: 6px;
  padding: 9px 1px;
  border-top: 1px solid var(--line);
}
.record-annotation-tooltip article:first-of-type {
  border-top: 0;
}
.record-annotation-tooltip p {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.record-annotation-tooltip .annotation-no-note {
  color: var(--tone-info-fg);
  font-style: italic;
}
.record-annotation-tooltip small {
  color: var(--muted);
}
.annotation-tooltip-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.annotation-tooltip-tags span {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--ui-accent-soft, #edf7f0);
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 700;
}
button:focus-visible,
input:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 760px) {
  .record-reading-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .record-reading-controls {
    width: 100%;
  }
  .record-reading-search {
    min-width: 0;
    flex: 1;
  }
  .record-reading-text {
    padding: 28px 22px;
  }
  .focus-mode {
    inset: 12px;
  }
  .focus-button {
    white-space: nowrap;
  }
}
@media (prefers-reduced-motion: reduce) {
  .record-reading-pane * {
    scroll-behavior: auto !important;
    transition: none !important;
  }
}
</style>

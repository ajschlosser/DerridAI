<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AppIcon from "./AppIcon.vue";
import OperationRow from "./OperationRow.vue";
import { useI18nStore } from "../stores/i18n";
import {
  classifyOperations,
  filterCounts,
  filterOperations,
  groupByDay,
  isActive,
  type OperationFilter,
  type OperationView,
  type OperationsBridge,
} from "../domain/operationsPanel";

const props = withDefaults(
  defineProps<{ bridge: OperationsBridge; undoMs?: number; historyLimit?: number }>(),
  { undoMs: 6000, historyLimit: 6 },
);
const i18n = useI18nStore();
const locale = computed(() => i18n.locale || "en-US");

const views = ref<OperationView[]>(props.bridge.snapshot());
const now = ref(Date.now());
const filter = ref<OperationFilter>("all");
const showAllHistory = ref(false);
const announcement = ref("");
const root = ref<HTMLElement | null>(null);
const heading = ref<HTMLElement | null>(null);
const fresh = ref<Set<string>>(new Set());

// ---- data + clock ------------------------------------------------------------------------
let unsubscribe: (() => void) | null = null;
let clock = 0;
const anyActive = computed(() => views.value.some(isActive));
function restartClock() {
  window.clearInterval(clock);
  clock = window.setInterval(
    () => {
      now.value = Date.now();
    },
    anyActive.value ? 1000 : 30_000,
  );
}
watch(anyActive, restartClock);

// ---- removal with undo (no confirm dialogs: a removal can simply be taken back) ------------
interface PendingUndo {
  message: string;
  timer: number;
  ids: string[];
  commit: () => Promise<void>;
}
const pending = ref<PendingUndo | null>(null);
const hiddenIds = computed(() => new Set(pending.value?.ids ?? []));
async function commitPending() {
  const current = pending.value;
  if (!current) return;
  window.clearTimeout(current.timer);
  pending.value = null;
  try {
    await current.commit();
  } catch (error) {
    announce(
      i18n.tf("operations.panel.removal_failed", "Could not remove: {error}", {
        error: error instanceof Error ? error.message : String(error),
      }),
    );
  }
}
function queueRemoval(message: string, ids: string[], commit: () => Promise<void>) {
  void commitPending(); // only one undo window at a time; settle the previous one
  const timer = window.setTimeout(() => {
    void commitPending();
  }, props.undoMs);
  pending.value = { message, timer, ids, commit };
  announce(
    `${message} ${i18n.t("operations.panel.undo_hint", "Undo is available for a few seconds.")}`,
  );
}
function undo() {
  const current = pending.value;
  if (!current) return;
  window.clearTimeout(current.timer);
  pending.value = null;
  announce(i18n.t("operations.panel.restored", "Restored."));
  void nextTick(() => root.value?.querySelector<HTMLElement>("[data-primary]")?.focus());
}
function removeOne(id: string) {
  const view = views.value.find((item) => item.id === id);
  if (!view) return;
  queueRemoval(
    i18n.tf("operations.panel.removed", "Removed {name}.", { name: view.label }),
    [id],
    () => props.bridge.remove(id),
  );
}
function clearFinished() {
  const ids = views.value.filter((view) => !isActive(view)).map((view) => view.id);
  if (!ids.length) return;
  queueRemoval(
    i18n.tf("operations.panel.cleared", "Cleared {count} finished operation(s).", {
      count: ids.length,
    }),
    ids,
    () => props.bridge.clearFinished(),
  );
}

// ---- announcements: one polite live region, only for outcomes, never for progress ticks ------
let announceTimer = 0;
function announce(message: string) {
  window.clearTimeout(announceTimer);
  announceTimer = window.setTimeout(() => {
    announcement.value = "";
    void nextTick(() => {
      announcement.value = message;
    });
  }, 250);
}
const OUTCOME_KEYS: Record<string, [string, string]> = {
  completed: ["operations.panel.announce_completed", "{name} completed."],
  failed: ["operations.panel.announce_failed", "{name} failed."],
  blocked: ["operations.panel.announce_blocked", "{name} needs attention."],
  cancelled: ["operations.panel.announce_cancelled", "{name} was cancelled."],
};

// ---- keep keyboard focus when the list changes under it -------------------------------------
let lastFocusedRow = "";
function onFocusIn(event: FocusEvent) {
  const row = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-op-id]");
  lastFocusedRow = row?.dataset.opId ?? "";
}
async function restoreFocusIfLost(hadFocus: boolean) {
  await nextTick();
  if (!hadFocus || (document.activeElement && document.activeElement !== document.body)) return;
  const target =
    (lastFocusedRow &&
      root.value?.querySelector<HTMLElement>(
        `[data-op-id="${CSS.escape(lastFocusedRow)}"] button:not([disabled])`,
      )) ||
    heading.value;
  target?.focus();
}

function onChange() {
  const before = new Map(views.value.map((view) => [view.id, view.status]));
  const hadFocus = Boolean(root.value?.contains(document.activeElement));
  const next = props.bridge.snapshot();
  const messages: string[] = [];
  const justDone = new Set<string>();
  for (const view of next) {
    const was = before.get(view.id);
    if (was && ["queued", "running", "cancelling"].includes(was) && OUTCOME_KEYS[view.status]) {
      const [key, fallback] = OUTCOME_KEYS[view.status];
      messages.push(i18n.tf(key, fallback, { name: view.label }));
      if (view.status === "completed") justDone.add(view.id);
    }
  }
  views.value = next;
  if (messages.length) announce(messages.join(" "));
  if (justDone.size) {
    fresh.value = new Set([...fresh.value, ...justDone]);
    window.setTimeout(() => {
      fresh.value = new Set([...fresh.value].filter((id) => !justDone.has(id)));
    }, 2400);
  }
  void restoreFocusIfLost(hadFocus);
}

onMounted(() => {
  unsubscribe = props.bridge.subscribe(onChange);
  restartClock();
  window.addEventListener("beforeunload", flushOnLeave);
});
onBeforeUnmount(() => {
  unsubscribe?.();
  window.clearInterval(clock);
  window.clearTimeout(announceTimer);
  window.removeEventListener("beforeunload", flushOnLeave);
  void commitPending(); // leaving the page settles a pending removal instead of dropping it
});
function flushOnLeave() {
  void commitPending();
}

async function refresh() {
  await props.bridge.refresh();
  announce(i18n.t("operations.panel.announce_updated", "Operations updated."));
}

// ---- derived lists --------------------------------------------------------------------------
const visible = computed(() => views.value.filter((view) => !hiddenIds.value.has(view.id)));
const counts = computed(() => filterCounts(visible.value));
const sections = computed(() => classifyOperations(filterOperations(visible.value, filter.value)));
const historyShown = computed(() =>
  showAllHistory.value
    ? sections.value.history
    : sections.value.history.slice(0, props.historyLimit),
);
const historyGroups = computed(() => groupByDay(historyShown.value, now.value, locale.value));
const hiddenHistory = computed(() =>
  Math.max(0, sections.value.history.length - props.historyLimit),
);
const empty = computed(() => visible.value.length === 0);
const filterEmpty = computed(
  () =>
    !empty.value &&
    !sections.value.active.length &&
    !sections.value.attention.length &&
    !sections.value.history.length,
);
const canClear = computed(() => visible.value.some((view) => !isActive(view)));

const FILTERS: Array<[OperationFilter, string, string]> = [
  ["all", "operations.panel.filter_all", "All"],
  ["active", "operations.panel.filter_active", "Running"],
  ["attention", "operations.panel.filter_attention", "Needs attention"],
  ["done", "operations.panel.filter_done", "Finished"],
];
</script>

<template>
  <section
    id="operationsPanel"
    ref="root"
    class="ops"
    aria-labelledby="ops-heading"
    @focusin="onFocusIn"
  >
    <header class="ops-head">
      <div class="ops-head-copy">
        <h2 id="ops-heading" ref="heading" tabindex="-1" class="ops-h2">
          {{ i18n.t("operations.background", "Background operations") }}
        </h2>
        <p class="ops-lede">
          {{
            i18n.t(
              "operations.shared_queue",
              "LLM, RAG, PDF corpus builds, and Chroma upserts share this queue",
            )
          }}
        </p>
      </div>
      <div class="ops-head-actions">
        <button type="button" class="ops-btn" id="refreshJobs" @click="refresh">
          <AppIcon name="refresh" />{{ i18n.t("ui.refresh", "Refresh") }}
        </button>
        <button
          type="button"
          class="ops-btn"
          id="clearFinishedJobs"
          :disabled="!canClear"
          @click="clearFinished"
        >
          {{ i18n.t("operations.panel.clear_finished", "Clear finished") }}
        </button>
      </div>
    </header>

    <div
      class="ops-filters"
      role="group"
      :aria-label="i18n.t('operations.panel.filter_label', 'Show operations')"
    >
      <button
        v-for="[id, key, fallback] in FILTERS"
        :key="id"
        type="button"
        class="ops-chip"
        :class="{ 'is-attention': id === 'attention' && counts.attention > 0 }"
        :aria-pressed="filter === id"
        @click="filter = id"
      >
        {{ i18n.t(key, fallback) }} <span class="ops-chip-count">{{ counts[id] }}</span>
      </button>
    </div>

    <div v-if="pending" class="ops-undo" role="group" :aria-label="pending.message">
      <span>{{ pending.message }}</span>
      <button type="button" class="ops-btn is-primary" @click="undo">
        {{ i18n.t("operations.panel.undo", "Undo") }}
      </button>
    </div>

    <div v-if="empty" class="ops-empty">
      <span class="ops-empty-art" aria-hidden="true"><AppIcon name="history" /></span>
      <h3>{{ i18n.t("operations.panel.empty_title", "Nothing in flight") }}</h3>
      <p>
        {{
          i18n.t(
            "operations.panel.empty_body",
            "Start a corpus build, install a language, or run a research question, and it will show up here.",
          )
        }}
      </p>
    </div>
    <p v-else-if="filterEmpty" class="ops-empty-inline">
      {{ i18n.t("operations.panel.empty_filtered", "No operations match this filter.") }}
    </p>

    <section v-if="sections.attention.length" class="ops-section" aria-labelledby="ops-h-attention">
      <h3 id="ops-h-attention" class="ops-h3">
        {{ i18n.t("operations.panel.section_attention", "Needs attention") }}
        <span class="ops-count">{{ sections.attention.length }}</span>
      </h3>
      <TransitionGroup tag="ul" name="ops-row" class="ops-list">
        <OperationRow
          v-for="view in sections.attention"
          :key="view.id"
          :view="view"
          :now="now"
          :fresh="fresh.has(view.id)"
          @details="bridge.openDetails"
          @result="bridge.openResult"
          @cancel="bridge.cancel"
          @remove="removeOne"
        />
      </TransitionGroup>
    </section>

    <section v-if="sections.active.length" class="ops-section" aria-labelledby="ops-h-active">
      <h3 id="ops-h-active" class="ops-h3">
        {{ i18n.t("operations.panel.section_active", "In progress") }}
        <span class="ops-count">{{ sections.active.length }}</span>
      </h3>
      <TransitionGroup tag="ul" name="ops-row" class="ops-list">
        <OperationRow
          v-for="view in sections.active"
          :key="view.id"
          :view="view"
          :now="now"
          :fresh="fresh.has(view.id)"
          @details="bridge.openDetails"
          @result="bridge.openResult"
          @cancel="bridge.cancel"
          @remove="removeOne"
        />
      </TransitionGroup>
    </section>

    <section v-if="sections.history.length" class="ops-section" aria-labelledby="ops-h-history">
      <h3 id="ops-h-history" class="ops-h3">
        {{ i18n.t("operations.panel.section_history", "History") }}
        <span class="ops-count">{{ sections.history.length }}</span>
      </h3>
      <div v-for="group in historyGroups" :key="group.key" class="ops-day">
        <h4 class="ops-day-label">{{ group.label }}</h4>
        <TransitionGroup tag="ul" name="ops-row" class="ops-list">
          <OperationRow
            v-for="view in group.items"
            :key="view.id"
            :view="view"
            :now="now"
            :fresh="fresh.has(view.id)"
            @details="bridge.openDetails"
            @result="bridge.openResult"
            @cancel="bridge.cancel"
            @remove="removeOne"
          />
        </TransitionGroup>
      </div>
      <button
        v-if="hiddenHistory > 0 || showAllHistory"
        type="button"
        class="ops-more"
        :aria-expanded="showAllHistory"
        @click="showAllHistory = !showAllHistory"
      >
        {{
          showAllHistory
            ? i18n.t("operations.panel.show_fewer", "Show fewer")
            : i18n.tf("operations.panel.show_all_history", "Show all {count}", {
                count: sections.history.length,
              })
        }}
      </button>
    </section>

    <div class="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {{ announcement }}
    </div>
  </section>
</template>

<style>
/* Operations panel. Namespaced (.ops-) and unscoped so the row component shares the rules. */
.ops {
  --ops-text: var(--text);
  --ops-muted: var(--muted);
  --ops-line: var(--line);
  --ops-control: var(--text-2);
  --ops-surface: var(--card);
  --ops-sunken: var(--soft);
  --ops-info-fg: var(--tone-info-fg);
  --ops-info-bg: var(--tone-info-bg);
  --ops-success-fg: var(--tone-ok-fg);
  --ops-success-bg: var(--tone-ok-bg);
  --ops-warning-fg: var(--tone-warn-fg);
  --ops-warning-bg: var(--tone-warn-bg);
  --ops-danger-fg: var(--tone-danger-fg);
  --ops-danger-bg: var(--tone-danger-bg);
  --ops-neutral-fg: var(--text-2);
  --ops-neutral-bg: var(--soft);
  --ops-accent: var(--ui-accent);
  --ops-radius: 14px;
  container-type: inline-size;
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--ops-line);
  border-radius: 18px;
  background: var(--ops-surface);
  color: var(--ops-text);
  box-shadow: var(--elev-1);
}
.ops-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: flex-start;
  justify-content: space-between;
}
.ops-h2 {
  margin: 0;
  font-size: 1.25rem;
  line-height: 1.25;
  letter-spacing: -0.01em;
}
.ops-h2:focus {
  outline: none;
}
.ops-h2:focus-visible {
  outline: 3px solid var(--ops-accent);
  outline-offset: 3px;
  border-radius: 6px;
}
.ops-lede {
  margin: 4px 0 0;
  color: var(--ops-muted);
  font-size: 0.875rem;
  line-height: 1.45;
  max-width: 60ch;
}
.ops-head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ops-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ops-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--ops-control);
  border-radius: 999px;
  background: var(--ops-surface);
  color: var(--ops-text);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.ops-chip:hover {
  background: var(--ops-sunken);
}
.ops-chip[aria-pressed="true"] {
  background: var(--ops-accent);
  border-color: var(--ops-accent);
  color: var(--accent-on);
}
.ops-chip-count {
  display: inline-grid;
  place-items: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--ops-neutral-bg);
  color: var(--ops-neutral-fg);
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}
.ops-chip[aria-pressed="true"] .ops-chip-count {
  background: var(--accent-on);
  color: var(--ops-accent);
}
.ops-chip.is-attention:not([aria-pressed="true"]) .ops-chip-count {
  background: var(--ops-warning-bg);
  color: var(--ops-warning-fg);
}
.ops-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--ops-control);
  border-radius: 10px;
  background: var(--ops-surface);
  color: var(--ops-text);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.05s;
}
.ops-btn :where(svg) {
  width: 16px;
  height: 16px;
}
.ops-btn:hover:not(:disabled) {
  background: var(--ops-sunken);
}
.ops-btn:active:not(:disabled) {
  transform: translateY(1px);
}
.ops-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ops-btn.is-primary {
  background: var(--ops-accent);
  border-color: var(--ops-accent);
  color: var(--accent-on);
}
.ops-btn.is-primary:hover:not(:disabled) {
  filter: brightness(0.94);
  background: var(--ops-accent);
}
.ops-btn.is-danger {
  border-color: var(--ops-danger-fg);
  color: var(--ops-danger-fg);
}
.ops-btn.is-danger:hover:not(:disabled) {
  background: var(--ops-danger-bg);
}
.ops-btn.is-quiet {
  border-color: transparent;
  color: var(--ops-muted);
}
.ops-btn.is-quiet:hover:not(:disabled) {
  background: var(--ops-sunken);
  color: var(--ops-text);
}
.ops :where(button):focus-visible,
.ops :where(.ops-more):focus-visible {
  outline: 3px solid var(--ops-accent) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 2px var(--ops-surface);
}
.ops-undo {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--ops-neutral-bg);
  color: var(--ops-neutral-fg);
  font-size: 0.9375rem;
  animation: ops-pop 0.2s ease-out;
}
.ops-section {
  display: grid;
  gap: 10px;
}
.ops-h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0 0;
  font-size: 0.8125rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ops-muted);
}
.ops-count {
  display: inline-grid;
  place-items: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--ops-neutral-bg);
  font-size: 0.8125rem;
  letter-spacing: 0;
  font-variant-numeric: tabular-nums;
}
.ops-day {
  display: grid;
  gap: 8px;
}
.ops-day-label {
  margin: 4px 0 0;
  font-size: 0.875rem;
  font-weight: 650;
  color: var(--ops-text);
}
.ops-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ops-row {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 6px 14px;
  align-items: start;
  padding: 14px 16px 14px 20px;
  border: 1px solid var(--ops-line);
  border-radius: var(--ops-radius);
  background: var(--ops-surface);
  scroll-margin-top: 96px;
  transition:
    border-color 0.15s,
    box-shadow 0.2s;
}
.ops-row:hover,
.ops-row:focus-within {
  border-color: var(--ops-control);
  box-shadow: var(--elev-2);
}
.ops-rail {
  position: absolute;
  inset: 10px auto 10px 0;
  width: 4px;
  border-radius: 0 4px 4px 0;
  background: var(--ops-neutral-fg);
  opacity: 0.35;
}
.ops-row.tone-info .ops-rail {
  background: var(--ops-info-fg);
  opacity: 1;
}
.ops-row.tone-success .ops-rail {
  background: var(--ops-success-fg);
  opacity: 0.7;
}
.ops-row.tone-warning .ops-rail {
  background: var(--ops-warning-fg);
  opacity: 1;
}
.ops-row.tone-danger .ops-rail {
  background: var(--ops-danger-fg);
  opacity: 1;
}
.ops-type {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--ops-sunken);
  color: var(--ops-neutral-fg);
}
.ops-type :where(svg) {
  width: 20px;
  height: 20px;
}
.ops-main {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.ops-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
}
.ops-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.ops-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 700;
  background: var(--ops-neutral-bg);
  color: var(--ops-neutral-fg);
}
.ops-status.tone-info {
  background: var(--ops-info-bg);
  color: var(--ops-info-fg);
}
.ops-status.tone-success {
  background: var(--ops-success-bg);
  color: var(--ops-success-fg);
}
.ops-status.tone-warning {
  background: var(--ops-warning-bg);
  color: var(--ops-warning-fg);
}
.ops-status.tone-danger {
  background: var(--ops-danger-bg);
  color: var(--ops-danger-fg);
}
.ops-status-icon {
  width: 14px;
  height: 14px;
  flex: none;
}
svg.ops-status-icon {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.ops-check path {
  stroke-dasharray: 16;
  stroke-dashoffset: 0;
}
.ops-row.is-fresh .ops-check path {
  animation: ops-draw 0.6s ease-out;
}
.ops-row.is-fresh {
  animation: ops-flash 1.6s ease-out;
}
.ops-dot {
  border-radius: 50%;
  background: currentColor;
  width: 8px;
  height: 8px;
}
.ops-spinner {
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: ops-spin 0.8s linear infinite;
}
.ops-spinner.is-queued {
  border-style: dotted;
  animation-duration: 2.4s;
}
.ops-subtitle,
.ops-meta,
.ops-progress-text {
  margin: 0;
  color: var(--ops-muted);
  font-size: 0.875rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.ops-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
}
.ops-progress-area {
  display: grid;
  gap: 4px;
  max-width: 560px;
}
.ops-progress {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: var(--ops-sunken);
  overflow: hidden;
}
.ops-progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  background: var(--ops-accent);
  transition: width 0.6s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.ops-row.is-active .ops-progress:not(.is-indeterminate) .ops-progress-fill {
  background-image: linear-gradient(
    110deg,
    transparent 30%,
    color-mix(in srgb, var(--accent-on) 35%, transparent) 50%,
    transparent 70%
  );
  background-size: 220px 100%;
  background-repeat: no-repeat;
  animation: ops-sheen 1.8s linear infinite;
}
.ops-progress.is-indeterminate .ops-progress-fill {
  width: 34%;
  animation: ops-slide 1.6s ease-in-out infinite;
}
.ops-progress-text {
  font-variant-numeric: tabular-nums;
}
.ops-error {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--ops-danger-bg);
  color: var(--ops-danger-fg);
  font-size: 0.875rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.ops-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 2px 0 0;
  font-size: 0.8125rem;
  color: var(--ops-muted);
}
.ops-facts div {
  display: flex;
  gap: 6px;
  min-width: 0;
}
.ops-facts dt {
  font-weight: 650;
}
.ops-facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.ops-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  align-self: center;
}
.ops-more {
  justify-self: start;
  min-height: 36px;
  padding: 0 4px;
  border: 0;
  background: none;
  color: var(--ops-accent);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
.ops-empty {
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: 40px 16px;
  text-align: center;
}
.ops-empty h3 {
  margin: 6px 0 0;
  font-size: 1.125rem;
}
.ops-empty p {
  margin: 0;
  max-width: 46ch;
  color: var(--ops-muted);
  line-height: 1.5;
}
.ops-empty-art {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: var(--ops-sunken);
  color: var(--ops-accent);
  animation: ops-float 4s ease-in-out infinite;
}
.ops-empty-art :where(svg) {
  width: 30px;
  height: 30px;
}
.ops-empty-inline {
  margin: 0;
  padding: 12px 0;
  color: var(--ops-muted);
}
.ops-row-enter-active,
.ops-row-leave-active {
  transition:
    opacity 0.25s,
    transform 0.25s;
}
.ops-row-move {
  transition: transform 0.3s;
}
.ops-row-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.ops-row-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
.ops-row-leave-active {
  position: absolute;
  left: 0;
  right: 0;
}
@keyframes ops-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes ops-sheen {
  from {
    background-position: -220px 0;
  }
  to {
    background-position: calc(100% + 220px) 0;
  }
}
@keyframes ops-slide {
  0% {
    transform: translateX(-110%);
  }
  100% {
    transform: translateX(320%);
  }
}
@keyframes ops-draw {
  from {
    stroke-dashoffset: 16;
  }
  to {
    stroke-dashoffset: 0;
  }
}
@keyframes ops-flash {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--ops-success-fg) 35%, transparent);
  }
  100% {
    box-shadow: 0 0 0 14px transparent;
  }
}
@keyframes ops-pop {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes ops-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}
@container (max-width:680px) {
  .ops-row {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .ops-actions {
    grid-column: 1/-1;
    justify-content: flex-start;
  }
}
@media (prefers-reduced-motion: reduce) {
  .ops *,
  .ops *::before,
  .ops *::after {
    animation: none !important;
    transition: none !important;
  }
  .ops-progress.is-indeterminate .ops-progress-fill {
    width: 34%;
    margin-left: 0;
  }
}
@media (forced-colors: active) {
  .ops-progress {
    border: 1px solid CanvasText;
  }
  .ops-progress-fill {
    background: Highlight;
  }
  .ops-rail {
    background: CanvasText;
    opacity: 1;
  }
  /* Do not depend on Highlight/HighlightText pairing: a thick border and underline say "pressed" in any palette. */
  .ops-chip[aria-pressed="true"] {
    background: Canvas;
    color: CanvasText;
    border: 3px solid Highlight;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .ops-chip-count,
  .ops-chip[aria-pressed="true"] .ops-chip-count {
    background: Canvas;
    color: CanvasText;
    border: 1px solid CanvasText;
  }
  .ops-dot {
    background: none;
    border: 2px solid CanvasText;
  }
  .ops-status {
    border: 1px solid CanvasText;
  }
  .ops-error {
    border: 1px solid CanvasText;
  }
  .ops-btn.is-primary {
    border-width: 2px;
  }
}
</style>

<style scoped>
/* OperationsPanel WCAG reflow hardening
 *
 * Keeps content shrinkable and wrappable for:
 * - WCAG 1.4.10 Reflow at 320 CSS px
 * - WCAG 1.4.4 200% text resize
 * - WCAG 1.4.12 increased text spacing
 *
 * Deliberately scoped to #operationsPanel. Do not replace this with
 * global overflow-x:hidden; that would conceal rather than fix overflow.
 */
#operationsPanel {
  box-sizing: border-box;
  inline-size: 100%;
  max-inline-size: 100%;
  min-inline-size: 0;
}

/*
 * Flex/grid descendants commonly retain min-width:auto, which prevents
 * them from shrinking below their intrinsic text width.
 */
#operationsPanel :where(
  header,
  footer,
  section,
  article,
  nav,
  div,
  ul,
  ol,
  li
) {
  min-inline-size: 0;
}

/*
 * Long job names, provider/model identifiers, paths, and translated
 * strings must remain reflowable instead of widening the panel.
 */
#operationsPanel :where(
  h1,
  h2,
  h3,
  h4,
  p,
  span,
  strong,
  small,
  code,
  output,
  label
) {
  max-inline-size: 100%;
  overflow-wrap: anywhere;
}

/*
 * Controls must tolerate larger text and text-spacing overrides.
 * Do not force controls into a fixed block-size.
 */
#operationsPanel :where(
  button,
  select,
  input
) {
  max-inline-size: 100%;
  min-block-size: 24px;
  block-size: auto;
}

#operationsPanel button {
  white-space: normal;
  overflow-wrap: anywhere;
}

/*
 * Common flex/grid action rows must be allowed to wrap. These selectors
 * are intentionally conditional: nonexistent class names do nothing.
 */
#operationsPanel :where(
  .operations-header,
  .operations-toolbar,
  .operations-controls,
  .operations-filters,
  .operation-row,
  .operation-main,
  .operation-summary,
  .operation-copy,
  .operation-meta,
  .operation-actions,
  .empty-state,
  .panel-actions
) {
  min-inline-size: 0;
  max-inline-size: 100%;
}

#operationsPanel :where(
  .operations-toolbar,
  .operations-controls,
  .operations-filters,
  .operation-actions,
  .panel-actions
) {
  flex-wrap: wrap;
}

/*
 * If any of these are grid containers, minmax(0,1fr) prevents the
 * content column from establishing an intrinsic minimum wider than
 * the available viewport.
 */
#operationsPanel :where(
  .operation-row,
  .operation-summary
) {
  grid-template-columns: minmax(0, 1fr) auto;
}

@media (max-width: 360px) {
  #operationsPanel :where(
    .operation-row,
    .operation-summary
  ) {
    grid-template-columns: minmax(0, 1fr);
  }

  #operationsPanel :where(
    .operation-actions,
    .panel-actions
  ) {
    inline-size: 100%;
  }
}
</style>

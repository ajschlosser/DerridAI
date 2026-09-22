<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { RecordHistoryItem } from "../../types/record";
const props = withDefaults(
  defineProps<{ items: RecordHistoryItem[]; total?: number; canOpen?: boolean }>(),
  { total: 0, canOpen: false },
);
const emit = defineEmits<{ open: [] }>();
const i18n = useI18nStore();
function when(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : new Intl.DateTimeFormat(i18n.locale, { dateStyle: "medium", timeStyle: "short" }).format(
        date,
      );
}
function fieldLabel(key: string) {
  return i18n.t(
    `field.${key}`,
    key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()),
  );
}
</script>
<template>
  <section class="record-history-timeline" aria-labelledby="recordHistoryHeading">
    <header>
      <div>
        <p>{{ i18n.t("record.audit_trail", "Audit trail") }}</p>
        <h3 id="recordHistoryHeading">{{ i18n.t("record.change_history", "Change history") }}</h3>
      </div>
      <span>{{ props.total }}</span>
    </header>
    <ol v-if="props.items.length">
      <li v-for="item in props.items" :key="item.id">
        <i aria-hidden="true"></i>
        <div>
          <strong>{{ fieldLabel(item.field_name || "field") }}</strong
          ><span
            >{{ item.source
            }}<template v-if="item.initiated_by"> · {{ item.initiated_by }}</template
            ><template v-if="item.model"> · {{ item.model }}</template></span
          ><small v-if="item.reason">{{ item.reason }}</small>
        </div>
        <time v-if="item.timestamp">{{ when(item.timestamp) }}</time>
      </li>
    </ol>
    <div v-else class="history-empty">
      {{ i18n.t("record.no_history", "No tracked record changes yet.") }}
    </div>
    <button
      v-if="props.canOpen && props.total"
      class="history-open"
      type="button"
      @click="emit('open')"
    >
      <AppIcon name="history" />{{ i18n.t("record.open_history", "Open history & undo") }}
    </button>
  </section>
</template>
<style scoped>
.record-history-timeline {
  display: grid;
  gap: 13px;
}
.record-history-timeline > header {
  display: flex;
  justify-content: space-between;
  align-items: end;
}
.record-history-timeline > header p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.record-history-timeline h3 {
  margin: 2px 0 0;
  font-size: 1rem;
}
.record-history-timeline > header > span {
  min-width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--soft);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.record-history-timeline ol {
  list-style: none;
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
}
.record-history-timeline li {
  position: relative;
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr) auto;
  gap: 9px;
  padding: 9px 0;
}
.record-history-timeline li:not(:last-child):after {
  content: "";
  position: absolute;
  left: 5px;
  top: 20px;
  bottom: -4px;
  width: 1px;
  background: var(--tone-ok-bg);
}
.record-history-timeline li > i {
  width: 11px;
  height: 11px;
  margin-top: 3px;
  border: 2px solid var(--card);
  border-radius: 50%;
  background: var(--ui-accent, #3c8d62);
  box-shadow: 0 0 0 1px var(--tone-ok-edge);
  z-index: 1;
}
.record-history-timeline li > div {
  display: grid;
  gap: 2px;
}
.record-history-timeline strong {
  font-size: 0.78125rem;
}
.record-history-timeline li span {
  color: var(--muted);
  font-size: 0.8125rem;
}
.record-history-timeline li small {
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.record-history-timeline time {
  color: var(--muted);
  font-size: 0.8125rem;
  text-align: right;
}
.history-empty {
  padding: 14px;
  border: 1px dashed var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  color: var(--muted);
  font-size: 0.78125rem;
}
.history-open {
  min-height: 36px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  color: var(--text-2);
  font-weight: 800;
  cursor: pointer;
}
.history-open :deep(svg) {
  width: 16px;
  height: 16px;
}
.history-open:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
</style>

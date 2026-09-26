<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import { metadataValueText } from "../domain/metadataValues";
import AppIcon from "./AppIcon.vue";

type Evidence = {
  block_ids?: string[];
  confidence?: number | null;
  reason?: string;
  reviewed_by?: string;
};
const props = defineProps<{
  evidence: Record<string, Evidence>;
  selectedField?: string;
  fields?: string[];
  /** The record's current values, so each row says what the evidence is for. */
  values?: Record<string, unknown>;
}>();
const emit = defineEmits<{ select: [field: string] }>();
const i18n = useI18nStore();

const spanCount = (field: string) => (props.evidence?.[field]?.block_ids || []).length;
const valueOf = (field: string) => metadataValueText(props.values?.[field]);
/** Fields with a value but no evidence come first: they are the work that is left. */
const fieldNames = computed(() =>
  Array.from(new Set([...(props.fields || []), ...Object.keys(props.evidence || {})]))
    .filter(Boolean)
    .sort((a, b) => {
      const need = (f: string) => (valueOf(f) && !spanCount(f) ? 0 : 1);
      return need(a) - need(b) || a.localeCompare(b);
    }),
);
const label = (field: string) => i18n.t(`record.${field}`, field.replace(/_/g, " "));
function select(field: string) {
  emit("select", props.selectedField === field ? "" : field);
}
function confidencePercent(field: string): number | null {
  const value = props.evidence?.[field]?.confidence;
  return typeof value === "number" && Number.isFinite(value) ? Math.round(value * 100) : null;
}
function countText(field: string) {
  const count = spanCount(field);
  return count
    ? i18n.tf(`pdf_corpus.evidence_span_count_${count === 1 ? "one" : "many"}`, { count })
    : i18n.t("pdf_corpus.evidence_none_yet");
}
</script>
<template>
  <ul
    v-if="fieldNames.length"
    class="evidence-list"
    :aria-label="i18n.t('pdf_corpus.field_evidence')"
  >
    <li v-for="field in fieldNames" :key="field">
      <button
        type="button"
        :aria-pressed="props.selectedField === field"
        :class="{ active: props.selectedField === field }"
        @click="select(String(field))"
      >
        <span class="ev-top">
          <b>{{ label(field) }}</b>
          <span class="ev-status" :data-state="spanCount(field) ? 'bound' : 'empty'">
            <AppIcon :name="spanCount(field) ? 'check' : 'warning'" />{{ countText(field) }}
            <template v-if="confidencePercent(field) !== null">
              · {{ confidencePercent(field) }}%</template
            >
          </span>
        </span>
        <span v-if="valueOf(field)" class="ev-value">{{ valueOf(field) }}</span>
        <small v-if="props.evidence?.[field]?.reason">{{ props.evidence[field]?.reason }}</small>
      </button>
    </li>
  </ul>
  <p v-else class="help">{{ i18n.t("pdf_corpus.no_evidence") }}</p>
</template>
<style scoped>
.evidence-list {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 6px;
  margin: 8px 0 0;
}
.evidence-list li {
  margin: 0;
}
.evidence-list button {
  width: 100%;
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  background: var(--surface-card, var(--soft));
  border: 1px solid var(--border-subtle, transparent);
  border-radius: var(--radius-control, 8px);
  text-align: start;
  color: inherit;
  cursor: pointer;
}
.evidence-list button:hover {
  background: var(--surface-hover, var(--soft));
}
.evidence-list button.active {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
  background: var(--surface-selected, var(--soft));
}
.evidence-list button:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.ev-top {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 2px 8px;
}
.evidence-list b {
  font-size: 0.875rem;
}
.ev-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8125rem;
  font-weight: 650;
}
.ev-status svg {
  inline-size: 0.875rem;
  block-size: 0.875rem;
}
.ev-status[data-state="bound"] {
  color: var(--tone-ok-fg);
}
.ev-status[data-state="empty"] {
  color: var(--tone-warn-fg);
}
.ev-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8125rem;
}
.evidence-list small,
.help {
  font-size: 0.8125rem;
  color: var(--muted);
}
</style>

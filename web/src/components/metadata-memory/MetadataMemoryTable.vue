<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref, watch } from "vue";
import type { MetadataMemoryEntry } from "../../api/metadataMemory";
import { useI18nStore } from "../../stores/i18n";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const {
  items,
  loading = false,
  filtered = false,
} = defineProps<{
  items: MetadataMemoryEntry[];
  loading?: boolean;
  filtered?: boolean;
}>();

const i18n = useI18nStore();
const expanded = ref<Set<string>>(new Set());
// A new page or filter result must not inherit the previous page's open rows.
watch(
  () => items,
  () => (expanded.value = new Set()),
);

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
function kindLabel(value: string): string {
  if (value === "positive") return i18n.t("metadata_memory.kind_positive");
  if (value === "correction") return i18n.t("metadata_memory.kind_correction");
  return value;
}
function sourceLabel(item: MetadataMemoryEntry): string {
  return `${item.record_id}${item.record_revision ? ` · r${item.record_revision}` : ""}`;
}
function pageLabel(item: MetadataMemoryEntry): string {
  const { page_start: start, page_end: end } = item;
  if (start === undefined || start === null || start === "") return "";
  return end !== undefined && end !== null && end !== "" && String(end) !== String(start)
    ? `${start}–${end}`
    : String(start);
}
const hasDetails = (item: MetadataMemoryEntry) =>
  Boolean(item.context_text || item.evidence_block_ids.length);
function toggle(id: string) {
  const next = new Set(expanded.value);
  if (!next.delete(id)) next.add(id);
  expanded.value = next;
}
</script>

<template>
  <div
    class="memory-table-scroll ui-table-scroll"
    tabindex="0"
    role="region"
    :aria-label="i18n.t('metadata_memory.table_scroll')"
    :aria-busy="loading"
  >
    <table class="memory-table ui-table" :class="{ 'is-loading': loading }">
      <thead>
        <tr>
          <th scope="col">{{ i18n.t("metadata_memory.field_value") }}</th>
          <th scope="col">{{ i18n.t("metadata_memory.authority") }}</th>
          <th scope="col">{{ i18n.t("metadata_memory.source") }}</th>
          <th scope="col">{{ i18n.t("metadata_memory.scope") }}</th>
          <th scope="col">{{ i18n.t("metadata_memory.evidence") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>
            <b>{{ item.field }}</b>
            <pre class="memory-value">{{ displayValue(item.value) }}</pre>
            <p
              v-if="item.kind === 'correction' && item.rejected_value !== undefined"
              class="negative-precedent"
            >
              <span>{{ i18n.t("metadata_memory.rejected_value") }}</span>
              {{ displayValue(item.rejected_value) }}
            </p>
          </td>
          <td>
            <div class="badge-row">
              <UiStatusBadge
                :label="kindLabel(item.kind)"
                :tone="item.kind === 'correction' ? 'warning' : 'success'"
              />
              <UiStatusBadge
                v-if="item.evidence_bound"
                :label="i18n.t('metadata_memory.bound')"
                tone="info"
              />
            </div>
            <small>{{ item.authority || "—" }}</small>
            <small v-if="item.review_method">{{ item.review_method }}</small>
          </td>
          <td>
            <b>{{ sourceLabel(item) }}</b>
            <small v-if="item.source_document_id">{{ item.source_document_id }}</small>
            <small v-if="pageLabel(item)">
              {{ i18n.t("metadata_memory.page") }} {{ pageLabel(item) }}
            </small>
            <UiStatusBadge
              v-if="item.source_current === false"
              :label="i18n.t('metadata_memory.source_stale')"
              tone="warning"
            />
            <UiStatusBadge
              v-if="item.evidence_current === false"
              :label="i18n.t('metadata_memory.evidence_stale')"
              tone="warning"
            />
          </td>
          <td>
            <small v-if="item.build_id">{{ item.build_id }}</small>
            <small v-if="item.schema_id || item.schema_version">
              {{ item.schema_id || "—"
              }}<template v-if="item.schema_version"> · {{ item.schema_version }}</template>
            </small>
            <small v-if="item.language || item.region_type">
              {{ item.language || "—"
              }}<template v-if="item.region_type"> · {{ item.region_type }}</template>
            </small>
          </td>
          <td class="evidence-cell">
            <p
              v-if="item.evidence_text"
              class="evidence-text"
              :class="{ clamped: !expanded.has(item.id) }"
            >
              {{ item.evidence_text }}
            </p>
            <p v-else-if="item.evidence_bound" class="note">
              {{ i18n.t("metadata_memory.evidence_unresolved") }}
            </p>
            <p v-else class="note">{{ i18n.t("metadata_memory.context_only") }}</p>
            <template v-if="expanded.has(item.id)">
              <small v-if="item.evidence_block_ids.length">
                {{ i18n.t("metadata_memory.blocks") }}: {{ item.evidence_block_ids.join(", ") }}
              </small>
              <div v-if="item.context_text" class="context">
                <strong>{{ i18n.t("metadata_memory.indexed_context") }}</strong>
                <p>{{ item.context_text }}</p>
              </div>
            </template>
            <button
              v-if="hasDetails(item) || (item.evidence_text?.length ?? 0) > 220"
              type="button"
              class="details-toggle"
              :aria-expanded="expanded.has(item.id)"
              @click="toggle(item.id)"
            >
              {{
                expanded.has(item.id)
                  ? i18n.t("metadata_memory.hide_details")
                  : i18n.t("metadata_memory.show_details")
              }}
            </button>
          </td>
        </tr>
        <tr v-if="!loading && !items.length">
          <td colspan="5" class="empty-cell">
            {{ filtered ? i18n.t("metadata_memory.empty") : i18n.t("metadata_memory.empty_none") }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.memory-table-scroll {
  max-height: min(70vh, 900px);
  border-block: 1px solid var(--border-subtle);
}
.memory-table-scroll:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: -3px;
}
.memory-table {
  width: 100%;
  min-width: 860px;
  border-collapse: collapse;
  transition: opacity var(--motion-fast, 120ms) var(--ease-standard, ease);
}
.memory-table.is-loading {
  opacity: 0.55;
}
.memory-table th,
.memory-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  text-align: start;
  vertical-align: top;
}
.memory-table th {
  position: sticky;
  z-index: 1;
  top: 0;
  font-size: 0.75rem;
  white-space: nowrap;
}
.memory-table td {
  min-width: 150px;
  font-size: 0.8125rem;
}
.memory-table td:first-child {
  min-width: 200px;
}
.memory-table td.evidence-cell {
  min-width: min(30rem, 40vw);
}
.memory-table small {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary, var(--muted));
  overflow-wrap: anywhere;
}
.memory-table :deep(.ui-status-badge) {
  margin-top: 6px;
}
.memory-value {
  max-width: 28rem;
  margin: 6px 0 0;
  font: inherit;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.negative-precedent {
  margin: 8px 0 0;
}
.negative-precedent span {
  display: block;
  color: var(--tone-warn-fg);
  font-weight: 700;
}
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.badge-row :deep(.ui-status-badge) {
  margin-top: 0;
}
.evidence-text {
  margin: 0 0 6px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.evidence-text.clamped {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  line-clamp: 4;
}
.note {
  margin: 0 0 6px;
  color: var(--text-secondary, var(--muted));
}
.context p {
  max-height: 14rem;
  margin: 4px 0 0;
  overflow: auto;
  line-height: 1.5;
  white-space: pre-wrap;
}
.details-toggle {
  display: block;
  margin-top: 6px;
  padding: 2px 0;
  border: 0;
  background: none;
  color: var(--accent-fg, var(--accent));
  font: inherit;
  font-weight: var(--fw-semibold, 650);
  text-decoration: underline;
  cursor: pointer;
}
.details-toggle:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: 2px;
}
.empty-cell {
  padding: 32px !important;
  text-align: center !important;
  color: var(--text-secondary, var(--muted));
}
@media (prefers-reduced-motion: reduce) {
  .memory-table {
    transition: none;
  }
}
</style>

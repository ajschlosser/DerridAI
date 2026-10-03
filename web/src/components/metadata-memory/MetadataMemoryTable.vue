<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { ref, watch } from "vue";
import type { MetadataMemoryEntry } from "../../api/metadataMemory";
import { useI18nStore } from "../../stores/i18n";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";

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
          <th scope="col">
            <span class="header-with-help">
              {{ i18n.t("metadata_memory.authority") }}
              <UiTooltip :text="i18n.t('metadata_memory.authority_help')" placement="bottom" />
            </span>
          </th>
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
              <span class="badge-with-help">
                <UiStatusBadge
                  :label="kindLabel(item.kind)"
                  :tone="item.kind === 'correction' ? 'warning' : 'success'"
                />
                <UiTooltip
                  :text="
                    item.kind === 'correction'
                      ? i18n.t('metadata_memory.kind_correction_help')
                      : i18n.t('metadata_memory.kind_positive_help')
                  "
                  placement="bottom"
                />
              </span>
              <span v-if="item.evidence_bound" class="badge-with-help">
                <UiStatusBadge :label="i18n.t('metadata_memory.bound')" tone="info" />
                <UiTooltip :text="i18n.t('metadata_memory.bound_help')" placement="bottom" />
              </span>
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
            <span v-if="item.source_current === false" class="badge-with-help">
              <UiStatusBadge :label="i18n.t('metadata_memory.source_stale')" tone="warning" />
              <UiTooltip :text="i18n.t('metadata_memory.source_stale_help')" placement="bottom" />
            </span>
            <span v-if="item.evidence_current === false" class="badge-with-help">
              <UiStatusBadge :label="i18n.t('metadata_memory.evidence_stale')" tone="warning" />
              <UiTooltip :text="i18n.t('metadata_memory.evidence_stale_help')" placement="bottom" />
            </span>
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
.header-with-help,
.badge-with-help,
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.header-with-help,
.badge-with-help {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
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

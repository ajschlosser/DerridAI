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
/**
 * Paged entity index: the accessible, complete route to every entity in the
 * semantic content map, independent of what the drawing shows.
 */
import { computed } from "vue";
import type { SemanticContentGraphView, SemanticIndexSort } from "../../api/corpus";
import { SEMANTIC_INDEX_PAGE as INDEX_PAGE } from "../../domain/semanticGraphLabels";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  index: SemanticContentGraphView["index"];
  nodeTotal: number;
  loading: boolean;
  selectedNodeId: string;
  hueClass: (type: string) => string;
}>();
const emit = defineEmits<{ focus: [id: string, label: string] }>();
const indexSort = defineModel<SemanticIndexSort>("sort", { required: true });
const indexOffset = defineModel<number>("offset", { required: true });
const i18n = useI18nStore();

const formatter = computed(() => new Intl.NumberFormat(i18n.locale || undefined));
function n(value: number) {
  return formatter.value.format(value || 0);
}
const pageText = computed(() => {
  const index = props.index;
  if (!index.total) return "";
  return i18n.tf("pdf_corpus.semantic_graph_page", {
    start: n(index.offset + 1),
    end: n(Math.min(index.total, index.offset + index.items.length)),
    total: n(index.total),
  });
});
</script>

<template>
  <section class="entity-index" aria-labelledby="semantic-graph-entity-index-title">
    <div class="entity-index-heading">
      <div>
        <h4 id="semantic-graph-entity-index-title">
          {{ i18n.t("pdf_corpus.semantic_graph_entity_index") }}
        </h4>
        <p>
          {{
            i18n.tf("pdf_corpus.semantic_graph_entity_index_count", {
              shown: n(index.total),
              total: n(nodeTotal),
            })
          }}
        </p>
      </div>
      <label class="toolbar-field narrow" for="semantic-graph-index-sort">
        <span>{{ i18n.t("pdf_corpus.semantic_graph_sort") }}</span>
        <select id="semantic-graph-index-sort" v-model="indexSort" class="control">
          <option value="mentions">
            {{ i18n.t("pdf_corpus.semantic_graph_sort_mentions") }}
          </option>
          <option value="degree">{{ i18n.t("pdf_corpus.semantic_graph_sort_degree") }}</option>
          <option value="records">
            {{ i18n.t("pdf_corpus.semantic_graph_sort_records") }}
          </option>
          <option value="label">{{ i18n.t("pdf_corpus.semantic_graph_sort_label") }}</option>
        </select>
      </label>
    </div>
    <div class="entity-index-table-wrap">
      <table class="entity-index-table">
        <thead>
          <tr>
            <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_entity") }}</th>
            <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_type") }}</th>
            <th scope="col" class="num">
              {{ i18n.t("pdf_corpus.semantic_graph_mentions_short") }}
            </th>
            <th scope="col" class="num">
              {{ i18n.t("pdf_corpus.semantic_graph_records_short") }}
            </th>
            <th scope="col" class="num">
              {{ i18n.t("pdf_corpus.semantic_graph_connections_short") }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="node in index.items"
            :key="node.id"
            :class="{ selected: node.id === selectedNodeId }"
          >
            <td>
              <button type="button" class="entity-link" @click="emit('focus', node.id, node.label)">
                {{ node.label }}
              </button>
              <small v-if="node.aliases?.length">{{ node.aliases.slice(0, 4).join(" · ") }}</small>
            </td>
            <td>
              <span :class="['type-pill', hueClass(node.type)]"
                ><i class="swatch" aria-hidden="true" />{{ node.type }}</span
              >
            </td>
            <td class="num">{{ n(node.mention_count) }}</td>
            <td class="num">{{ n(node.record_count) }}</td>
            <td class="num">{{ n(node.degree) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="index.total > INDEX_PAGE" class="pager">
      <button
        type="button"
        class="btn secondary"
        :disabled="indexOffset === 0 || loading"
        @click="indexOffset = Math.max(0, indexOffset - INDEX_PAGE)"
      >
        {{ i18n.t("pdf_corpus.semantic_graph_prev_page") }}
      </button>
      <span>{{ pageText }}</span>
      <button
        type="button"
        class="btn secondary"
        :disabled="indexOffset + INDEX_PAGE >= index.total || loading"
        @click="indexOffset += INDEX_PAGE"
      >
        {{ i18n.t("pdf_corpus.semantic_graph_next_page") }}
      </button>
    </div>
  </section>
</template>

<style scoped>
/* Entity index */
.entity-index {
  display: grid;
  gap: var(--space-2);
}
.entity-index-heading {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: var(--space-3);
}
.entity-index-heading h4,
.entity-index-heading p {
  margin: 0;
}
.entity-index-heading p {
  margin-top: 2px;
  color: var(--muted);
  font-size: var(--fs-xs);
}
.entity-index-table-wrap {
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
}
.entity-index-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-xs);
}
.entity-index-table th,
.entity-index-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--line);
  text-align: start;
  vertical-align: top;
}
.entity-index-table .num {
  text-align: end;
  font-variant-numeric: tabular-nums;
}
.entity-index-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface-raised);
  font-weight: var(--fw-semibold);
}
.entity-index-table tbody tr:hover,
.entity-index-table tbody tr.selected {
  background: var(--surface-hover);
}
.entity-index-table td:first-child {
  min-width: 220px;
}
.entity-index-table td:first-child small {
  display: block;
  margin-top: 2px;
  color: var(--muted);
}
.entity-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-weight: var(--fw-semibold);
  text-align: start;
  cursor: pointer;
}
.entity-link:hover {
  text-decoration: underline;
}
.pager {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--fs-xs);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.entity-link:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
.toolbar-field {
  display: grid;
  gap: 4px;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--muted);
}
.toolbar-field.search {
  flex: 1 1 260px;
}
.toolbar-field.narrow .control {
  width: 9rem;
}
.icon-btn:focus-visible,
.entity-link:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
.btn.clear {
  align-self: end;
}
.hue-2 {
  --hue: var(--viz-cat-2);
}
.hue-3 {
  --hue: var(--viz-cat-3);
}
.hue-4 {
  --hue: var(--viz-cat-4);
}
.hue-5 {
  --hue: var(--viz-cat-5);
}
.hue-6 {
  --hue: var(--viz-cat-6);
}
.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--hue, var(--accent));
  flex: none;
}
.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  text-transform: capitalize;
}
.icon-btn {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.icon-btn:hover {
  background: var(--surface-hover);
}
.icon-btn.small {
  width: 24px;
  height: 24px;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>

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
 * Lists under the semantic map: for a Record step, the entities in it and the
 * Records that share them; for an entity step, its relations and Records.
 * Observational relations stay labelled apart from semantic ones, which carry
 * their reviewer authority.
 */
import { computed } from "vue";
import type {
  RecordSemanticMap,
  RecordSemanticMapNode,
  SemanticContentGraphEdge,
  SemanticNodeNeighborhood,
} from "../../api/corpus";
import { nodeTone, relationLabel } from "../../features/corpus-builder/domain/semanticMap";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  map: RecordSemanticMap | null;
  neighborhood: SemanticNodeNeighborhood | null;
  recordId: string;
  idPrefix: string;
}>();
const emit = defineEmits<{
  walkToNode: [node: { id: string; label: string }];
  walkToRecord: [recordId: string];
  openRecord: [recordId: string];
}>();
const i18n = useI18nStore();

const AUTHORITY_STATUSES = new Set(["human_confirmed", "unreviewed", "disputed"]);
function authorityLabel(status?: string) {
  const value = status || "unreviewed";
  return AUTHORITY_STATUSES.has(value)
    ? i18n.t(`pdf_corpus.semantic_map_authority_${value}`)
    : value.replaceAll("_", " ");
}
const localNodesByType = computed(() => {
  const groups = new Map<string, RecordSemanticMapNode[]>();
  for (const node of props.map?.nodes || []) {
    if (!node.local) continue;
    const bucket = groups.get(node.type) || [];
    bucket.push(node);
    groups.set(node.type, bucket);
  }
  return Array.from(groups.entries()).sort(([left], [right]) =>
    left === "term" ? 1 : right === "term" ? -1 : left.localeCompare(right),
  );
});
function neighborOf(edge: SemanticContentGraphEdge) {
  const hood = props.neighborhood;
  if (!hood) return null;
  const otherId = edge.source === hood.node.id ? edge.target : edge.source;
  return hood.nodes.find((node) => node.id === otherId) || null;
}
</script>

<template>
  <div v-if="map" class="semantic-map-lists">
    <section v-if="localNodesByType.length" :aria-labelledby="`${idPrefix}-semantic-local-title`">
      <h4 :id="`${idPrefix}-semantic-local-title`">
        {{ i18n.t("pdf_corpus.semantic_map_in_record") }}
      </h4>
      <dl class="node-groups">
        <template v-for="[type, nodes] in localNodesByType" :key="type">
          <dt>{{ type }}</dt>
          <dd>
            <button
              v-for="node in nodes"
              :key="node.id"
              type="button"
              class="node-chip"
              :data-tone="nodeTone(node.type)"
              @click="emit('walkToNode', node)"
            >
              {{ node.label }}<small>{{ node.record_count || 1 }}</small>
            </button>
          </dd>
        </template>
      </dl>
    </section>

    <section :aria-labelledby="`${idPrefix}-semantic-linked-title`">
      <h4 :id="`${idPrefix}-semantic-linked-title`">
        {{ i18n.t("pdf_corpus.semantic_map_linked_records") }}
      </h4>
      <p class="help">{{ i18n.t("pdf_corpus.semantic_map_linked_records_help") }}</p>
      <p v-if="!map.linked_records.length" class="semantic-map-status">
        {{ i18n.t("pdf_corpus.semantic_map_no_links") }}
      </p>
      <ul v-else class="record-links">
        <li v-for="link in map.linked_records" :key="link.record_id">
          <div class="record-link-head">
            <b>{{ link.record_id }}</b>
            <small>{{
              i18n.tf("pdf_corpus.semantic_map_shared", { count: link.shared_node_count })
            }}</small>
          </div>
          <p>{{ link.preview }}</p>
          <div class="record-link-shared">
            <button
              v-for="node in link.shared_nodes"
              :key="node.id"
              type="button"
              class="node-chip"
              :data-tone="nodeTone(node.type)"
              @click="emit('walkToNode', node)"
            >
              {{ node.label }}
            </button>
          </div>
          <div class="record-link-actions">
            <button type="button" class="btn small" @click="emit('walkToRecord', link.record_id)">
              {{ i18n.t("pdf_corpus.semantic_map_explore_record") }}
            </button>
            <button
              type="button"
              class="btn small secondary"
              @click="emit('openRecord', link.record_id)"
            >
              {{ i18n.t("pdf_corpus.semantic_map_open_record") }}
            </button>
          </div>
        </li>
      </ul>
    </section>
  </div>

  <!-- Node step lists ---------------------------------------------------------------------------------------- -->
  <div v-else-if="neighborhood" class="semantic-map-lists">
    <section :aria-labelledby="`${idPrefix}-semantic-relations-title`">
      <h4 :id="`${idPrefix}-semantic-relations-title`">
        {{
          i18n.tf("pdf_corpus.semantic_map_relations", {
            shown: neighborhood.edges.length,
            total: neighborhood.total_edges,
          })
        }}
      </h4>
      <p v-if="!neighborhood.edges.length" class="semantic-map-status">
        {{ i18n.t("pdf_corpus.semantic_map_no_relations") }}
      </p>
      <ul v-else class="relation-list">
        <li v-for="edge in neighborhood.edges" :key="edge.id" :data-kind="edge.relation_kind">
          <span class="relation-line">
            <span v-if="edge.target === neighborhood.node.id" aria-hidden="true">←</span>
            <b>{{ relationLabel(edge) }}</b>
            <span v-if="edge.source === neighborhood.node.id" aria-hidden="true">→</span>
            <button
              v-if="neighborOf(edge)"
              type="button"
              class="node-chip"
              :data-tone="nodeTone(neighborOf(edge)!.type)"
              @click="emit('walkToNode', neighborOf(edge)!)"
            >
              {{ neighborOf(edge)!.label }}
            </button>
          </span>
          <small>
            {{
              edge.relation_kind === "semantic"
                ? `${i18n.t("pdf_corpus.semantic_graph_semantic")} · ${authorityLabel(edge.authority_status)}`
                : i18n.t("pdf_corpus.semantic_graph_observational")
            }}
            ·
            {{
              i18n.tf("pdf_corpus.semantic_map_relation_records", {
                count: edge.record_ids?.length || 0,
              })
            }}
          </small>
        </li>
      </ul>
    </section>
    <section :aria-labelledby="`${idPrefix}-semantic-node-records-title`">
      <h4 :id="`${idPrefix}-semantic-node-records-title`">
        {{
          i18n.tf("pdf_corpus.semantic_map_records_for_node", {
            shown: neighborhood.records.length,
            total: neighborhood.total_records,
          })
        }}
      </h4>
      <ul class="record-links">
        <li v-for="row in neighborhood.records" :key="row.record_id">
          <div class="record-link-head">
            <b>{{ row.record_id }}</b>
            <small v-if="row.record_id === recordId">{{
              i18n.t("pdf_corpus.semantic_map_current_record")
            }}</small>
          </div>
          <p>{{ row.preview }}</p>
          <div class="record-link-actions">
            <button type="button" class="btn small" @click="emit('walkToRecord', row.record_id)">
              {{ i18n.t("pdf_corpus.semantic_map_explore_record") }}
            </button>
            <button
              v-if="row.record_id !== recordId"
              type="button"
              class="btn small secondary"
              @click="emit('openRecord', row.record_id)"
            >
              {{ i18n.t("pdf_corpus.semantic_map_open_record") }}
            </button>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.semantic-map-lists {
  display: grid;
  gap: var(--space-4);
}
.semantic-map-lists section {
  display: grid;
  gap: var(--space-2);
}
.node-groups {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: var(--space-2) var(--space-3);
  margin: 0;
}
.node-groups dt {
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--muted);
}
.node-groups dd {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
}
.node-chip {
  display: inline-flex;
  gap: 4px;
  align-items: baseline;
  padding: 2px var(--space-2);
  border: 1px solid var(--line);
  border-inline-start: 3px solid var(--border-strong);
  border-radius: var(--radius-control);
  background: var(--card);
  color: var(--text);
  font: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.node-chip small {
  color: var(--muted);
}
.node-chip[data-tone="person"] {
  border-inline-start-color: var(--tone-info-edge);
}
.node-chip[data-tone="concept"] {
  border-inline-start-color: var(--accent);
}
.node-chip[data-tone="work"] {
  border-inline-start-color: var(--tone-ok-edge);
}
.node-chip[data-tone="entity"] {
  border-inline-start-color: var(--tone-warn-edge);
}
.record-links,
.relation-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.record-links li,
.relation-list li {
  display: grid;
  gap: 4px;
  padding-block: var(--space-2);
  border-top: 1px solid var(--line);
}
.record-links p {
  color: var(--muted);
  font-size: var(--fs-xs);
}
.record-link-head,
.relation-line {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}
.record-link-head small,
.relation-list small {
  color: var(--muted);
  font-size: var(--fs-xs);
}
.record-link-shared,
.record-link-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.relation-list li[data-kind="observational"] b {
  font-weight: var(--fw-regular);
  font-style: italic;
}
.semantic-map-lists h4,
.record-links p {
  margin: 0;
}
.semantic-map-status,
.help {
  color: var(--muted);
  font-size: var(--fs-xs);
  margin: 0;
}
.semantic-map-status.warning {
  color: var(--tone-warn-fg);
}
.semantic-map-status.error {
  color: var(--tone-danger-fg);
}
.node-chip:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
</style>

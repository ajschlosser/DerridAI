<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/**
 * Inspector for the selected entity in the semantic content map: counts,
 * character profile and grouped relations. Semantic relations keep their
 * authority status; observational ones stay visibly weaker.
 */
import { computed } from "vue";
import type {
  SemanticContentGraphView,
  SemanticGraphViewEdge,
  SemanticGraphViewNode,
  SemanticGraphViewRelation,
} from "../../api/corpus";
import { authorityLabel as authorityText, relationLabel } from "../../domain/semanticGraphLabels";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  selectedNode: SemanticGraphViewNode | null;
  focusDetail: SemanticContentGraphView["focus"] | null;
  selectedEdges: SemanticGraphViewEdge[];
  nodesById: Map<string, SemanticGraphViewNode>;
  focusId: string;
  hueClass: (type: string) => string;
}>();
const emit = defineEmits<{
  clear: [];
  focus: [id: string, label: string];
  select: [id: string];
}>();
const i18n = useI18nStore();

const formatter = computed(() => new Intl.NumberFormat(i18n.locale || undefined));
function n(value: number) {
  return formatter.value.format(value || 0);
}
const relationGroups = computed(() => {
  const relations = props.focusDetail?.relations || [];
  return [
    {
      kind: "semantic",
      title: i18n.t("pdf_corpus.semantic_graph_semantic_relations"),
      items: relations.filter((rel) => rel.relation_kind === "semantic"),
    },
    {
      kind: "observational",
      title: i18n.t("pdf_corpus.semantic_graph_observational_relations"),
      items: relations.filter((rel) => rel.relation_kind !== "semantic"),
    },
  ].filter((group) => group.items.length);
});
function featureText(values?: Array<{ label: string; count?: number }>) {
  return (values || [])
    .slice(0, 8)
    .map((item) => (Number(item.count || 0) > 1 ? `${item.label} ×${item.count}` : item.label))
    .join(" · ");
}
function relationKey(rel: SemanticGraphViewRelation) {
  return `${rel.id}:${rel.direction}`;
}
</script>

<template>
  <aside class="graph-inspector" :aria-label="i18n.t('pdf_corpus.semantic_graph_inspector')">
    <template v-if="selectedNode">
      <div class="inspector-head">
        <p :class="['type-pill', hueClass(selectedNode.type)]">
          <i class="swatch" aria-hidden="true" />{{ selectedNode.type }}
        </p>
        <UiTooltip
          :text="i18n.t('pdf_corpus.semantic_graph_clear_selection')"
          trigger-mode="content"
          :content-focusable="false"
          placement="bottom"
        >
          <button
            type="button"
            class="icon-btn small"
            :aria-label="i18n.t('pdf_corpus.semantic_graph_clear_selection')"
            @click="emit('clear')"
          >
            ×
          </button>
        </UiTooltip>
      </div>
      <h4>{{ selectedNode.label }}</h4>
      <p v-if="selectedNode.aliases?.length" class="graph-aliases">
        {{ selectedNode.aliases.join(" · ") }}
      </p>
      <dl class="stat-row">
        <div>
          <dt>{{ i18n.t("pdf_corpus.semantic_graph_mentions_short") }}</dt>
          <dd>{{ n(selectedNode.mention_count) }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("pdf_corpus.semantic_graph_records_short") }}</dt>
          <dd>{{ n(selectedNode.record_count) }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("pdf_corpus.semantic_graph_connections_short") }}</dt>
          <dd>{{ n(selectedNode.degree) }}</dd>
        </div>
      </dl>
      <button
        v-if="selectedNode.id !== focusId"
        type="button"
        class="btn primary focus-btn"
        :aria-label="i18n.tf('pdf_corpus.semantic_graph_focus_on', { label: selectedNode.label })"
        @click="emit('focus', selectedNode.id, selectedNode.label)"
      >
        {{ i18n.t("pdf_corpus.semantic_graph_focus_action") }}
      </button>

      <div v-if="focusDetail?.node.character_profile" class="character-profile">
        <h5>{{ i18n.t("pdf_corpus.semantic_graph_character_profile") }}</h5>
        <dl>
          <template v-if="focusDetail.node.character_profile.actions_as_agent?.length">
            <dt>{{ i18n.t("pdf_corpus.semantic_graph_actions_agent") }}</dt>
            <dd>{{ featureText(focusDetail.node.character_profile.actions_as_agent) }}</dd>
          </template>
          <template v-if="focusDetail.node.character_profile.actions_as_patient?.length">
            <dt>{{ i18n.t("pdf_corpus.semantic_graph_actions_patient") }}</dt>
            <dd>{{ featureText(focusDetail.node.character_profile.actions_as_patient) }}</dd>
          </template>
          <template v-if="focusDetail.node.character_profile.possessions?.length">
            <dt>{{ i18n.t("pdf_corpus.semantic_graph_possessions") }}</dt>
            <dd>{{ featureText(focusDetail.node.character_profile.possessions) }}</dd>
          </template>
          <template v-if="focusDetail.node.character_profile.modifiers?.length">
            <dt>{{ i18n.t("pdf_corpus.semantic_graph_modifiers") }}</dt>
            <dd>{{ featureText(focusDetail.node.character_profile.modifiers) }}</dd>
          </template>
        </dl>
        <small>{{ i18n.t("pdf_corpus.semantic_graph_character_profile_note") }}</small>
      </div>

      <template v-if="focusDetail">
        <p class="relations-count">
          {{
            i18n.tf("pdf_corpus.semantic_graph_relations_count", {
              shown: n(focusDetail.relations.length),
              total: n(focusDetail.relations_total),
            })
          }}
        </p>
        <section v-for="group in relationGroups" :key="group.kind" class="relation-group">
          <h5>{{ group.title }}</h5>
          <ul class="relation-list">
            <li v-for="rel in group.items" :key="relationKey(rel)">
              <div class="relation-line">
                <span class="predicate">
                  <span aria-hidden="true">{{ rel.direction === "outgoing" ? "→" : "←" }}</span>
                  <span class="visually-hidden">{{
                    rel.direction === "outgoing"
                      ? i18n.t("pdf_corpus.semantic_graph_direction_outgoing")
                      : i18n.t("pdf_corpus.semantic_graph_direction_incoming")
                  }}</span>
                  {{ relationLabel(rel.predicate) }}
                </span>
                <button
                  type="button"
                  :class="['entity-link', hueClass(rel.other_type)]"
                  @click="emit('focus', rel.other_id, rel.other_label)"
                >
                  {{ rel.other_label }}
                </button>
              </div>
              <div class="relation-meta">
                <span
                  v-if="rel.relation_kind === 'semantic'"
                  :class="['badge', rel.authority_status]"
                >
                  {{ authorityText(rel.authority_status, i18n.t) }}
                </span>
                <small>{{
                  i18n.tf("pdf_corpus.semantic_graph_occurrences", {
                    count: n(rel.count),
                    records: n(rel.record_count),
                  })
                }}</small>
                <small v-if="rel.evidence_ref_count">{{
                  i18n.tf("pdf_corpus.semantic_graph_evidence_refs", {
                    count: n(rel.evidence_ref_count),
                  })
                }}</small>
                <small v-if="rel.observed_verbs.length">{{
                  i18n.tf("pdf_corpus.semantic_graph_observed_verbs", {
                    verbs: rel.observed_verbs.join(" · "),
                  })
                }}</small>
              </div>
            </li>
          </ul>
        </section>
      </template>
      <ul v-else-if="selectedEdges.length" class="relation-list compact">
        <li v-for="edge in selectedEdges.slice(0, 12)" :key="edge.id">
          <div class="relation-line">
            <span class="predicate">{{ relationLabel(edge.predicate) }}</span>
            <button
              type="button"
              class="entity-link"
              @click="emit('select', edge.source === selectedNode.id ? edge.target : edge.source)"
            >
              {{
                nodesById.get(edge.source === selectedNode.id ? edge.target : edge.source)?.label
              }}
            </button>
          </div>
        </li>
      </ul>
    </template>
    <div v-else class="inspector-empty">
      <p>{{ i18n.t("pdf_corpus.semantic_graph_select_node") }}</p>
    </div>
  </aside>
</template>

<style scoped>
/* Inspector */
.graph-inspector {
  display: grid;
  align-content: start;
  gap: var(--space-2);
  max-height: 78vh;
  overflow: auto;
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
}
.inspector-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.inspector-empty {
  display: grid;
  place-items: center;
  min-height: 200px;
  color: var(--muted);
  text-align: center;
}
.graph-inspector h4 {
  font-size: var(--fs-lg, 1.125rem);
  overflow-wrap: anywhere;
}
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  margin: var(--space-1, 4px) 0;
}
.stat-row div {
  padding: var(--space-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-inset);
}
.stat-row dt {
  font-size: var(--fs-xs);
  color: var(--muted);
}
.stat-row dd {
  margin: 0;
  font-weight: var(--fw-semibold);
  font-variant-numeric: tabular-nums;
}
.focus-btn {
  justify-self: start;
}
.character-profile {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
}
.character-profile h5,
.character-profile dl,
.character-profile dd,
.relation-group h5 {
  margin: 0;
}
.character-profile dl {
  display: grid;
  gap: var(--space-2);
}
.character-profile dt {
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--muted);
}
.character-profile dd {
  overflow-wrap: anywhere;
}
.character-profile small {
  color: var(--muted);
}
.relations-count {
  padding-top: var(--space-2);
  border-top: 1px solid var(--line);
  font-size: var(--fs-xs);
}
.relation-group {
  display: grid;
  gap: var(--space-1, 4px);
}
.relation-group h5 {
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.relation-list {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}
.relation-list li {
  display: grid;
  gap: 4px;
  padding-block: var(--space-2);
  border-top: 1px solid var(--line);
}
.relation-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}
.predicate {
  font-size: var(--fs-xs);
  color: var(--muted);
}
.relation-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
}
.relation-meta small {
  color: var(--muted);
  font-size: var(--fs-xs);
}
.badge {
  padding: 1px 8px;
  border: 1px solid;
  border-radius: 999px;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--tone-warn-fg);
  background: var(--tone-warn-bg);
  border-color: var(--tone-warn-border);
}
.badge.human_confirmed {
  color: var(--tone-ok-fg);
  background: var(--tone-ok-bg);
  border-color: var(--tone-ok-border);
}
.badge.disputed {
  color: var(--tone-danger-fg);
  background: var(--tone-danger-bg);
  border-color: var(--tone-danger-border);
}
.graph-aliases,
.relations-count {
  color: var(--muted);
}
.graph-inspector h4,
.graph-inspector p {
  margin: 0;
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
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>

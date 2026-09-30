<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import type { PipelineDefinitionFilters } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { pipelineDefinitionStatusLabel, pipelineKey } from "../../domain/pipelinePresentation";
import {
  groupPipelineVersions,
  pipelineStatusTone,
  type PipelineVersionGroup,
} from "../../domain/pipelineStudioPresentation";
import {
  pipelineCategory,
  purposeById,
  purposeLabelFor,
  purposeText,
  termLabel,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = withDefaults(
  defineProps<{
    pipelines: PipelineDefinition[];
    assignments: PipelineAssignment[];
    purposes: PipelinePurpose[];
    vocabulary: PipelineWorkflowVocabulary;
    selectedKey: string;
    /** Selected workflow category ID; empty for all workflows. */
    workflow?: string;
    filters?: PipelineDefinitionFilters;
  }>(),
  { workflow: "", filters: () => ({ query: "", status: "" }) },
);

const emit = defineEmits<{
  select: [key: string];
  "update:workflow": [category: string];
  "update:filters": [filters: PipelineDefinitionFilters];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const expanded = ref(new Set<string>());

const categoryLabels = computed(
  () => new Map(props.vocabulary.categories.map((term) => [term.id, termLabel(term, t)])),
);

function searchText(pipeline: PipelineDefinition) {
  const purpose = purposeById(props.purposes, pipeline.purpose);
  return [
    pipeline.name,
    pipeline.pipeline_id,
    pipeline.purpose,
    String(pipeline.version),
    purpose ? purposeText(purpose, "label", t) : "",
    categoryLabels.value.get(pipelineCategory(pipeline, props.purposes)) || "",
  ]
    .join(" ")
    .toLowerCase();
}

const matching = computed(() => {
  const needle = props.filters.query.trim().toLowerCase();
  return props.pipelines.filter((pipeline) => {
    if (props.filters.status && pipeline.status !== props.filters.status) return false;
    return !needle || searchText(pipeline).includes(needle);
  });
});

const counts = computed(() => {
  const values = new Map<string, number>();
  for (const group of groupPipelineVersions(matching.value, props.assignments, props.purposes)) {
    values.set(group.category, (values.get(group.category) || 0) + 1);
  }
  return values;
});

const visibleVersions = computed(() =>
  props.workflow
    ? matching.value.filter(
        (pipeline) => pipelineCategory(pipeline, props.purposes) === props.workflow,
      )
    : matching.value,
);
const allGroups = computed(() =>
  groupPipelineVersions(visibleVersions.value, props.assignments, props.purposes),
);
type NavigatorSection = {
  id: string;
  category: PipelineWorkflowVocabulary["categories"][number] | null;
  groups: PipelineVersionGroup[];
};
const sections = computed<NavigatorSection[]>(() => {
  const classified = props.vocabulary.categories
    .map((category) => ({
      id: category.id,
      category,
      groups: allGroups.value.filter((group) => group.category === category.id),
    }))
    .filter((section) => section.groups.length);
  const unregistered = allGroups.value.filter(
    (group) => !purposeById(props.purposes, group.purpose),
  );
  // Pipelines whose purpose is unregistered stay visible instead of silently disappearing.
  return unregistered.length && !props.workflow
    ? [...classified, { id: "unclassified", category: null, groups: unregistered }]
    : classified;
});

function containsSelected(group: PipelineVersionGroup) {
  return group.versions.some((version) => pipelineKey(version) === props.selectedKey);
}
watch(
  () => props.selectedKey,
  () => {
    const group = allGroups.value.find(containsSelected);
    if (group) expanded.value = new Set(expanded.value).add(group.pipelineId);
  },
  { immediate: true },
);
function toggle(group: PipelineVersionGroup) {
  const next = new Set(expanded.value);
  if (next.has(group.pipelineId)) next.delete(group.pipelineId);
  else next.add(group.pipelineId);
  expanded.value = next;
}

function groupStatus(group: PipelineVersionGroup) {
  const assigned = group.assignedVersion
    ? `${t("pipelines.group_active", "Active")} v${group.assignedVersion.version}`
    : "";
  const latest = group.latestVersion;
  let other = "";
  if (latest.version !== group.assignedVersion?.version) {
    const label =
      latest.status === "draft"
        ? t("pipelines.status_draft", "Draft")
        : t("pipelines.group_latest", "Latest");
    other = `${label} v${latest.version}`;
  }
  return { assigned, other };
}
function versionCount(group: PipelineVersionGroup) {
  return group.versions.length === 1
    ? t("pipelines.version_count_one", "1 version")
    : i18n.tf("pipelines.version_count", "{count} versions", { count: group.versions.length });
}
function versionLabel(version: PipelineDefinition, group: PipelineVersionGroup) {
  const status =
    group.assignedVersion?.version === version.version
      ? t("pipelines.group_active", "Active")
      : pipelineDefinitionStatusLabel(version.status, t);
  return `v${version.version} · ${status}`;
}
function updateFilters(patch: Partial<PipelineDefinitionFilters>) {
  emit("update:filters", { ...props.filters, ...patch });
}
</script>

<template>
  <aside
    class="pipeline-definition-navigator"
    :aria-label="t('pipelines.definitions', 'Pipeline definitions')"
  >
    <div class="navigator-heading">
      <strong class="heading-with-help">
        {{ t("pipelines.definitions", "Pipeline definitions") }}
        <UiTooltip
          :text="
            t(
              'pipelines.definitions_help',
              'Each pipeline keeps every saved version. Select a pipeline to open its active or latest version, or expand it to choose an exact immutable version.',
            )
          "
        />
      </strong>
      <span class="navigator-count" role="status">
        {{
          i18n.tf("pipelines.definition_summary", "{pipelines} pipelines · {versions} versions", {
            pipelines: allGroups.length,
            versions: visibleVersions.length,
          })
        }}
      </span>
    </div>

    <form class="navigator-filters" @submit.prevent>
      <label>
        <span class="sr-only">{{ t("pipelines.search_definitions", "Search pipelines") }}</span>
        <input
          class="control"
          type="search"
          :value="filters.query"
          :placeholder="t('pipelines.search_definitions', 'Search pipelines')"
          :aria-label="t('pipelines.search_definitions', 'Search pipelines')"
          @input="updateFilters({ query: ($event.target as HTMLInputElement).value })"
        />
      </label>
      <div class="filter-pair">
        <label>
          <span>{{ t("pipelines.used_for", "Used for") }}</span>
          <select
            class="control"
            :value="workflow"
            @change="emit('update:workflow', ($event.target as HTMLSelectElement).value)"
          >
            <option value="">{{ t("pipelines.filter_all", "All") }}</option>
            <option
              v-for="category in vocabulary.categories"
              :key="category.id"
              :value="category.id"
            >
              {{ termLabel(category, t) }} ({{ counts.get(category.id) || 0 }})
            </option>
          </select>
        </label>
        <label>
          <span>{{ t("pipelines.filter_status", "Status") }}</span>
          <select
            class="control"
            :value="filters.status"
            @change="updateFilters({ status: ($event.target as HTMLSelectElement).value })"
          >
            <option value="">{{ t("pipelines.filter_all_statuses", "All statuses") }}</option>
            <option value="active">{{ t("pipelines.status_active", "Active") }}</option>
            <option value="draft">{{ t("pipelines.status_draft", "Draft") }}</option>
            <option value="disabled">{{ t("pipelines.status_disabled", "Disabled") }}</option>
          </select>
        </label>
      </div>
    </form>

    <p v-if="!allGroups.length" class="navigator-empty">
      {{ t("pipelines.no_definition_matches", "No pipelines match these filters.") }}
    </p>

    <section
      v-for="section in sections"
      :key="section.id"
      class="workflow-group"
      :data-category="section.category?.id"
      :aria-labelledby="`pipeline-workflow-${section.id}`"
    >
      <h3 :id="`pipeline-workflow-${section.id}`" class="group-heading">
        {{
          section.category
            ? termLabel(section.category, t)
            : t("pipelines.unregistered_purpose", "Unregistered purpose")
        }}
      </h3>
      <div v-for="group in section.groups" :key="group.pipelineId" class="pipeline-group">
        <button
          type="button"
          class="pipeline-choice"
          :class="{ selected: containsSelected(group) }"
          :aria-current="containsSelected(group) ? 'true' : undefined"
          @click="group.selectedVersion && emit('select', pipelineKey(group.selectedVersion))"
        >
          <strong>{{ group.displayName }}</strong>
          <span class="choice-meta">
            <template v-if="section.category">
              {{ purposeLabelFor(purposes, group.purpose, t) }}
            </template>
            <code v-else>{{ group.purpose }}</code>
          </span>
          <span class="choice-status">
            <UiStatusBadge
              v-if="groupStatus(group).assigned"
              :label="groupStatus(group).assigned"
              tone="info"
              :show-dot="false"
            />
            <span v-if="groupStatus(group).other">{{ groupStatus(group).other }}</span>
          </span>
        </button>
        <button
          type="button"
          class="version-toggle"
          :aria-expanded="expanded.has(group.pipelineId)"
          :aria-controls="`pipeline-versions-${group.pipelineId}`"
          @click="toggle(group)"
        >
          <span class="toggle-caret" aria-hidden="true"></span>
          {{ versionCount(group) }}
        </button>
        <ul
          v-if="expanded.has(group.pipelineId)"
          :id="`pipeline-versions-${group.pipelineId}`"
          class="version-list"
          :aria-label="group.displayName"
        >
          <li v-for="version in group.versions" :key="pipelineKey(version)">
            <button
              type="button"
              class="version-choice"
              :class="{ selected: pipelineKey(version) === selectedKey }"
              :aria-current="pipelineKey(version) === selectedKey ? 'true' : undefined"
              @click="emit('select', pipelineKey(version))"
            >
              <span>{{ versionLabel(version, group) }}</span>
              <UiStatusBadge
                v-if="version.status !== 'active'"
                :label="pipelineDefinitionStatusLabel(version.status, t)"
                :tone="pipelineStatusTone(version.status)"
                :show-dot="false"
              />
            </button>
          </li>
        </ul>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.pipeline-definition-navigator {
  align-self: start;
  position: sticky;
  top: var(--pipeline-studio-sticky-top, var(--space-3));
  max-height: var(--pipeline-studio-pane-max-height, min(76dvh, 960px));
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.navigator-heading {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-card);
}
.navigator-count {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.navigator-filters {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}
.filter-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}
.filter-pair label {
  display: grid;
  gap: 2px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.navigator-filters .control {
  width: 100%;
  min-height: var(--control-height-small);
}
.workflow-group {
  border-bottom: 1px solid var(--border-subtle);
}
.workflow-group:last-child {
  border-bottom: 0;
}
.group-heading {
  margin: 0;
  padding: var(--space-3) var(--space-3) var(--space-1);
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.pipeline-group {
  display: grid;
}
.pipeline-choice {
  position: relative;
  display: grid;
  gap: 2px;
  width: 100%;
  min-height: 44px;
  padding: var(--space-2) var(--space-3);
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.pipeline-choice strong {
  font-size: 0.875rem;
}
.choice-meta,
.choice-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.pipeline-choice:hover,
.pipeline-choice.selected {
  background: var(--surface-selected);
}
.pipeline-choice:focus-visible,
.version-toggle:focus-visible,
.version-choice:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -2px;
}
.pipeline-choice.selected::before {
  position: absolute;
  inset: 8px auto 8px 0;
  width: 3px;
  border-radius: 999px;
  background: var(--accent);
  content: "";
}
.version-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  width: 100%;
  min-height: 32px;
  padding: 0 var(--space-3) var(--space-2);
  border: 0;
  background: transparent;
  color: var(--text-tertiary);
  font: inherit;
  font-size: 0.8125rem;
  text-align: left;
  cursor: pointer;
}
.toggle-caret {
  display: inline-block;
  width: 0;
  height: 0;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  border-left: 5px solid currentColor;
  transition: transform var(--motion-fast) var(--ease-standard);
}
.version-toggle[aria-expanded="true"] .toggle-caret {
  transform: rotate(90deg);
}
.version-list {
  margin: 0 0 var(--space-2);
  padding: 0;
  list-style: none;
}
.version-choice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
  min-height: 34px;
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-6, 24px);
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.8125rem;
  text-align: left;
  cursor: pointer;
}
.version-choice:hover,
.version-choice.selected {
  background: var(--surface-selected);
  color: var(--text-primary);
}
.version-choice.selected {
  font-weight: var(--fw-bold);
}
.navigator-empty {
  margin: 0;
  padding: var(--space-3);
  color: var(--text-tertiary);
  font-size: 0.875rem;
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
.heading-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
@media (max-width: 960px) {
  .pipeline-definition-navigator {
    position: static;
    max-height: 360px;
  }
}
</style>

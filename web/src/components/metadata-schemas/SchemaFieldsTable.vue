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
/* eslint-disable vue/no-mutating-props -- the parent hands over its draft on purpose; these components edit it in place and the parent tracks dirtiness by comparing the whole draft. */
import { computed, nextTick, ref, watch } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import { useI18nStore } from "../../stores/i18n";
import {
  CORE_FIELDS,
  CORE_GROUP,
  blankField,
  type MetadataSchema,
  type SchemaField,
} from "../../api/metadataSchemas";
import AppIcon from "../AppIcon.vue";
import UiButton from "../ui/UiButton.vue";
import UiInput from "../ui/UiInput.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import SchemaFieldForm from "./SchemaFieldForm.vue";

// Fields are navigation first and editing second: select a field from the grouped navigator,
// then configure it in a stable inspector. This keeps browsing available for read-only built-ins
// and avoids placing a very large form inside a table row.
const props = defineProps<{ draft: MetadataSchema; readonly: boolean }>();
const { t } = useSchemaCopy();

const root = ref<HTMLElement | null>(null);
const filter = ref("");
const selected = ref<SchemaField | null>(props.draft.fields[0] || null);
watch(
  () => props.draft,
  (next) => {
    filter.value = "";
    selected.value = next.fields[0] || null;
  },
);
const groupKeys = computed(() => props.draft.groups.map((g) => g.key));
const i18n = useI18nStore();

/**
 * Fields a retrieval policy may name as analogy conditions: the locked core and every
 * other saved field. A field without a stable identity yet (never saved) is left out,
 * because a policy must reference identities, not names that may still change.
 */
function matchOptionsFor(field: SchemaField) {
  const core = CORE_FIELDS.map((name) => ({
    fieldId: `core.${name}`,
    label: i18n.t(`field.${name}`),
  }));
  const others = props.draft.fields
    .filter((other) => other.field_id && other.field_id !== field.field_id)
    .map((other) => ({ fieldId: other.field_id, label: other.label || other.name }));
  return [...core, ...others];
}

const needle = computed(() => filter.value.trim().toLowerCase());
const sections = computed(() =>
  props.draft.groups.map((group) => {
    const all = props.draft.fields.filter((field) => field.group === group.key);
    const shown = needle.value
      ? all.filter((field) => `${field.name} ${field.label}`.toLowerCase().includes(needle.value))
      : all;
    return { group, all, shown };
  }),
);
const totalShown = computed(() => sections.value.reduce((count, section) => count + section.shown.length, 0));

function policy(field: SchemaField) {
  const memory =
    field.retrieval_profile.enabled && Number(field.retrieval_profile.max_items || 0) > 0;
  return [
    field.evidence && t("evidence_short", "Evidence"),
    field.assess && t("assess_short", "Confidence"),
    field.review && t("review_short", "Human review"),
    memory && t("memory_short", "Memory"),
    field.review_visibility === "hidden" && t("hidden_short", "Hidden"),
  ].filter(Boolean) as string[];
}

function selectField(field: SchemaField) {
  selected.value = field;
}

async function addField(group: string) {
  const field = blankField(group);
  props.draft.fields.push(field);
  filter.value = "";
  await nextTick();
  selected.value = props.draft.fields[props.draft.fields.length - 1];
  await nextTick();
  root.value?.querySelector<HTMLInputElement>(".field-inspector input[maxlength='40']")?.focus();
}

async function removeField(field: SchemaField) {
  const fields = props.draft.fields;
  const index = fields.indexOf(field);
  if (index < 0) return;

  const sameGroup = fields.filter((candidate) => candidate.group === field.group);
  const groupIndex = sameGroup.indexOf(field);
  const replacement =
    sameGroup[groupIndex + 1] ||
    sameGroup[groupIndex - 1] ||
    fields[index + 1] ||
    fields[index - 1] ||
    null;

  fields.splice(index, 1);
  if (selected.value === field) selected.value = replacement;
  await nextTick();

  if (replacement) {
    const replacementIndex = props.draft.fields.indexOf(replacement);
    root.value
      ?.querySelector<HTMLButtonElement>(`[data-field-index="${replacementIndex}"]`)
      ?.focus();
  } else {
    root.value?.querySelector<HTMLButtonElement>(".add-field-button")?.focus();
  }
}

/** Reorder within a group: swap with the nearest neighbour that shares the group. */
function moveField(field: SchemaField, by: -1 | 1) {
  const fields = props.draft.fields;
  const from = fields.indexOf(field);
  let to = from + by;
  while (to >= 0 && to < fields.length && fields[to].group !== field.group) to += by;
  if (from < 0 || to < 0 || to >= fields.length) return;
  [fields[from], fields[to]] = [fields[to], fields[from]];
}

function isEdge(field: SchemaField, by: -1 | 1) {
  const list = props.draft.fields.filter((candidate) => candidate.group === field.group);
  return list[by === -1 ? 0 : list.length - 1] === field;
}
</script>

<template>
  <!-- eslint-disable vue/no-mutating-props -->
  <div ref="root" class="fields-panel">
    <div class="panel-toolbar">
      <label class="panel-search">
        <span class="sr-only">{{ t("filter_fields", "Filter fields") }}</span>
        <AppIcon class="panel-search-icon" name="search" aria-hidden="true" />
        <UiInput
          v-model="filter"
          type="search"
          autocomplete="off"
          :placeholder="t('filter_fields', 'Filter fields')"
        />
      </label>
      <p class="panel-count" role="status">
        {{ t("col_fields", "Fields") }}:
        {{ needle ? `${totalShown} / ${draft.fields.length}` : draft.fields.length }}
      </p>
      <p class="locked-core" role="note">
        <AppIcon name="lock" aria-hidden="true" />
        <b>{{ t("locked_core", "Locked core") }}</b>
        <code v-for="name in CORE_FIELDS" :key="name">{{ name }}</code>
        <UiTooltip :text="t('locked_core_help')" />
      </p>
    </div>

    <div class="fields-workspace">
      <nav class="field-navigator" :aria-label="t('fields', 'Fields')">
        <section v-for="section in sections" :key="section.group.key" class="field-group">
          <header class="field-group-header">
            <div>
              <h3>{{ section.group.label }}</h3>
              <p>
                <code>{{ section.group.key }}</code>
                <span v-if="section.group.key === CORE_GROUP">
                  · {{ t("holds_core", "holds the locked core") }}
                </span>
              </p>
            </div>
            <UiButton
              size="small"
              icon="plus"
              button-class="add-field-button"
              :disabled="readonly"
              :label="t('add_field', 'Add a field')"
              @click="addField(section.group.key)"
            />
          </header>

          <p v-if="!section.all.length" class="field-group-empty">
            {{ t("no_fields_in_group", "No fields in this group yet.") }}
          </p>
          <p v-else-if="needle && !section.shown.length" class="field-group-empty">
            {{ t("no_match", "No fields match the filter.") }}
          </p>

          <ul v-if="section.shown.length" class="field-list">
            <li
              v-for="field in section.shown"
              :key="field.field_id || draft.fields.indexOf(field)"
              class="field-list-item"
              :class="{ selected: selected === field }"
            >
              <button
                type="button"
                class="field-select"
                :data-field-index="draft.fields.indexOf(field)"
                :aria-current="selected === field ? 'true' : undefined"
                @click="selectField(field)"
              >
                <span class="field-select-main">
                  <span class="field-title">
                    {{ field.label || field.name || t("new_field", "New metadata field") }}
                  </span>
                  <code v-if="field.name">{{ field.name }}</code>
                </span>
                <span class="field-meta">
                  <span class="chip">{{ t(`type_${field.type}`, field.type) }}</span>
                  <span v-if="field.role && field.role !== 'scholarly'" class="chip">
                    {{ t(`role_${field.role}`, field.role) }}
                  </span>
                  <span v-for="label in policy(field)" :key="label" class="chip is-policy">{{ label }}</span>
                </span>
              </button>

              <div class="field-actions" :aria-label="t('actions', 'Actions')">
                <UiButton
                  icon-only
                  size="small"
                  icon="download"
                  button-class="flip"
                  :label="t('up', 'Move up')"
                  :disabled="readonly || isEdge(field, -1)"
                  @click="moveField(field, -1)"
                />
                <UiButton
                  icon-only
                  size="small"
                  icon="download"
                  :label="t('down', 'Move down')"
                  :disabled="readonly || isEdge(field, 1)"
                  @click="moveField(field, 1)"
                />
                <UiButton
                  icon-only
                  size="small"
                  icon="trash"
                  :label="t('remove_field', 'Remove field')"
                  :disabled="readonly"
                  @click="removeField(field)"
                />
              </div>
            </li>
          </ul>
        </section>
      </nav>

      <section
        v-if="selected"
        class="field-inspector"
        :aria-labelledby="`field-inspector-${draft.fields.indexOf(selected)}`"
      >
        <header class="field-inspector-header">
          <p class="field-inspector-kicker">{{ t("field_configuration", "Field configuration") }}</p>
          <h3 :id="`field-inspector-${draft.fields.indexOf(selected)}`">
            {{ selected.label || selected.name || t("new_field", "New metadata field") }}
          </h3>
          <p>{{ t("field_configuration_help", "Configure what this field means and how DerridAI should populate and review it.") }}</p>
        </header>
        <fieldset class="field-inspector-controls" :disabled="readonly">
          <SchemaFieldForm
            :field="selected"
            :group-keys="groupKeys"
            :match-options="matchOptionsFor(selected)"
          />
        </fieldset>
      </section>

      <section v-else class="field-inspector field-inspector-empty" aria-live="polite">
        <AppIcon name="edit" aria-hidden="true" />
        <h3>{{ t("select_field", "Select a field") }}</h3>
        <p>{{ t("select_field_help", "Choose a field to configure it, or add a new field to a prompt group.") }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.fields-panel {
  display: grid;
  gap: var(--space-3);
}
.panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  align-items: center;
}
.panel-search {
  position: relative;
  flex: 1 1 14rem;
  max-inline-size: 24rem;
}
.panel-search :deep(.ui-control) {
  padding-inline-start: 2.125rem;
}
.panel-search-icon {
  position: absolute;
  z-index: 1;
  inset-inline-start: 0.625rem;
  inset-block-start: 50%;
  translate: 0 -50%;
  inline-size: 1rem;
  block-size: 1rem;
  color: var(--text-tertiary);
  pointer-events: none;
}
.panel-count {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
}
.locked-core {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  align-items: center;
  margin: 0 0 0 auto;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.locked-core :deep(svg) {
  inline-size: 0.875rem;
  block-size: 0.875rem;
}
code {
  padding: 0.0625rem 0.375rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xs);
  background: var(--surface-inset);
  font-size: var(--fs-xs);
}
.fields-workspace {
  display: grid;
  grid-template-columns: minmax(18rem, 0.8fr) minmax(0, 1.4fr);
  gap: var(--space-4);
  align-items: start;
}
.field-navigator,
.field-inspector {
  min-inline-size: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.field-navigator {
  overflow: hidden;
}
.field-group + .field-group {
  border-block-start: 1px solid var(--border-subtle);
}
.field-group-header {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--surface-inset);
}
.field-group-header h3,
.field-group-header p {
  margin: 0;
}
.field-group-header h3 {
  font-size: var(--fs-base);
}
.field-group-header p {
  margin-block-start: var(--space-1);
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.field-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.field-list-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
  border-block-start: 1px solid var(--border-subtle);
}
.field-list-item:first-child {
  border-block-start: 0;
}
.field-list-item.selected {
  box-shadow: inset 3px 0 0 var(--accent-fg);
  background: var(--surface-selected);
}
.field-select {
  display: grid;
  gap: var(--space-2);
  inline-size: 100%;
  min-block-size: var(--control-height);
  padding: var(--space-3);
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.field-select:hover {
  background: var(--surface-hover);
}
.field-select:focus-visible {
  position: relative;
  z-index: 1;
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: calc(var(--focus-ring-offset) * -1);
}
.field-select-main {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}
.field-title {
  font-size: var(--fs-base);
  font-weight: var(--fw-bold);
}
.field-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.chip {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.chip.is-policy {
  background: var(--surface-selected);
  color: var(--accent-fg);
}
.field-actions {
  display: flex;
  gap: var(--space-1);
  padding-inline-end: var(--space-2);
}
.field-actions :deep(.flip svg) {
  rotate: 180deg;
}
.field-group-empty {
  margin: 0;
  padding: var(--space-4);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.field-inspector {
  position: sticky;
  inset-block-start: calc(var(--control-height) + var(--space-6));
  overflow: clip;
}
.field-inspector-header {
  padding: var(--space-4);
  border-block-end: 1px solid var(--border-subtle);
  background: var(--surface-inset);
}
.field-inspector-header h3,
.field-inspector-header p {
  margin: 0;
}
.field-inspector-header h3 {
  margin-block: var(--space-1) var(--space-2);
  font-size: var(--fs-lg);
}
.field-inspector-header > p:last-child {
  max-inline-size: var(--measure);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.field-inspector-kicker {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.field-inspector-controls {
  margin: 0;
  padding: var(--space-4);
  border: 0;
  min-inline-size: 0;
}
.field-inspector-empty {
  display: grid;
  place-items: center;
  min-block-size: 18rem;
  padding: var(--space-6);
  text-align: center;
}
.field-inspector-empty :deep(svg) {
  inline-size: 1.5rem;
  block-size: 1.5rem;
  color: var(--text-tertiary);
}
.field-inspector-empty h3,
.field-inspector-empty p {
  margin: 0;
}
.field-inspector-empty p {
  max-inline-size: 32rem;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
@media (max-width: 960px) {
  .fields-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
  .field-inspector {
    position: static;
  }
  .locked-core {
    margin-inline-start: 0;
  }
}
@media (max-width: 560px) {
  .field-list-item {
    grid-template-columns: minmax(0, 1fr);
  }
  .field-actions {
    padding: 0 var(--space-3) var(--space-3);
  }
}
</style>

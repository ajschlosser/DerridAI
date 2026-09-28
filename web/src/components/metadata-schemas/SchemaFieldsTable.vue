<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/* eslint-disable vue/no-mutating-props -- the parent hands over its draft on purpose; these components edit it in place and the parent tracks dirtiness by comparing the whole draft. */
import { computed, nextTick, ref } from "vue";
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
import UiTooltip from "../ui/UiTooltip.vue";
import SchemaFieldForm from "./SchemaFieldForm.vue";

// A schema's fields as a scannable table, one section per prompt group. Each row states the field's policy
// (evidence, confidence, human review, memory) at a glance, which the specification asks a schema editor to
// publish; a row expands in place into the full form so nothing needs a page of its own.
const props = defineProps<{ draft: MetadataSchema; readonly: boolean }>();
const { t } = useSchemaCopy();

const root = ref<HTMLElement | null>(null);
const filter = ref("");
const open = ref<SchemaField | null>(null);
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
    const all = props.draft.fields.filter((f) => f.group === group.key);
    const shown = needle.value
      ? all.filter((f) => `${f.name} ${f.label}`.toLowerCase().includes(needle.value))
      : all;
    return { group, all, shown };
  }),
);
const totalShown = computed(() => sections.value.reduce((n, s) => n + s.shown.length, 0));

const toggle = (field: SchemaField) => (open.value = open.value === field ? null : field);

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

async function addField(group: string) {
  const field = blankField(group);
  props.draft.fields.push(field);
  filter.value = "";
  await nextTick();
  // Pick up the reactive proxy the array now holds, so the new row expands and can be focused.
  open.value = props.draft.fields[props.draft.fields.length - 1];
  await nextTick();
  root.value?.querySelector<HTMLInputElement>('.field-form input[maxlength="40"]')?.focus();
}
function removeField(field: SchemaField) {
  const index = props.draft.fields.indexOf(field);
  if (index < 0) return;
  props.draft.fields.splice(index, 1);
  if (open.value === field) open.value = null;
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
  const list = props.draft.fields.filter((f) => f.group === field.group);
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
        <input
          v-model="filter"
          type="search"
          autocomplete="off"
          :placeholder="t('filter_fields', 'Filter fields')"
        />
      </label>
      <p class="panel-count" role="status">
        {{ needle ? `${totalShown} / ${draft.fields.length}` : draft.fields.length }}
        {{ t("fields", "Fields").toLowerCase() }}
      </p>
      <p class="locked-core" role="note">
        <AppIcon name="lock" aria-hidden="true" />
        <b>{{ t("locked_core", "Locked core") }}</b>
        <code v-for="name in CORE_FIELDS" :key="name">{{ name }}</code>
        <UiTooltip :text="t('locked_core_help')" />
      </p>
    </div>

    <div class="ui-table-scroll table-frame">
      <table class="fields-table ui-table" :aria-label="t('fields', 'Fields')">
        <thead>
          <tr>
            <th scope="col">{{ t("field_label", "Label") }}</th>
            <th scope="col">{{ t("field_type", "Type") }}</th>
            <th scope="col">{{ t("field_policy", "Field policy") }}</th>
            <th scope="col" class="actions-col">
              <span class="sr-only">{{ t("actions", "Actions") }}</span>
            </th>
          </tr>
        </thead>
        <template v-for="section in sections" :key="section.group.key">
          <tbody>
            <tr class="group-row">
              <th colspan="3" scope="colgroup">
                {{ section.group.label }}
                <code>{{ section.group.key }}</code>
                <small v-if="section.group.key === CORE_GROUP">{{
                  t("holds_core", "holds the locked core")
                }}</small>
              </th>
              <td class="actions-col">
                <UiButton
                  size="small"
                  icon="plus"
                  :disabled="readonly"
                  :label="t('add_field', 'Add a field')"
                  @click="addField(section.group.key)"
                />
              </td>
            </tr>
            <tr v-if="!section.all.length" class="empty-row">
              <td colspan="4">{{ t("no_fields_in_group", "No fields in this group yet.") }}</td>
            </tr>
            <template
              v-for="field in section.shown"
              :key="field.field_id || draft.fields.indexOf(field)"
            >
              <tr class="field-row" :class="{ selected: open === field }" @click="toggle(field)">
                <td>
                  <button
                    type="button"
                    class="row-toggle"
                    :aria-expanded="open === field"
                    :aria-controls="`field-detail-${field.name || 'new'}`"
                  >
                    <span class="chevron" :class="{ open: open === field }" aria-hidden="true"
                      >▸</span
                    >
                    <span class="row-title">{{
                      field.label || field.name || t("new_field", "New metadata field")
                    }}</span>
                  </button>
                  <code v-if="field.name" class="row-name">{{ field.name }}</code>
                </td>
                <td>
                  <span class="chip">{{ field.type }}</span>
                  <span v-if="field.role && field.role !== 'scholarly'" class="chip">{{
                    field.role
                  }}</span>
                </td>
                <td>
                  <span v-for="label in policy(field)" :key="label" class="chip is-policy">{{
                    label
                  }}</span>
                </td>
                <td class="actions-col" @click.stop>
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
                </td>
              </tr>
              <tr v-if="open === field" class="detail-row">
                <td :id="`field-detail-${field.name || 'new'}`" colspan="4">
                  <SchemaFieldForm
                    :field="field"
                    :group-keys="groupKeys"
                    :match-options="matchOptionsFor(field)"
                  />
                </td>
              </tr>
            </template>
            <tr v-if="needle && section.all.length && !section.shown.length" class="empty-row">
              <td colspan="4">{{ t("no_match", "No fields match the filter.") }}</td>
            </tr>
          </tbody>
        </template>
      </table>
    </div>
  </div>
</template>

<style scoped>
.fields-panel {
  display: grid;
  gap: 10px;
}
.panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  align-items: center;
}
.panel-search {
  position: relative;
  flex: 1 1 14rem;
  max-inline-size: 22rem;
}
.panel-search input {
  inline-size: 100%;
  min-block-size: 36px;
  padding-inline-start: 34px;
}
.panel-search-icon {
  position: absolute;
  inset-inline-start: 10px;
  inset-block-start: 50%;
  translate: 0 -50%;
  inline-size: 16px;
  block-size: 16px;
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
  gap: 6px;
  align-items: center;
  margin: 0 0 0 auto;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.locked-core :deep(svg) {
  inline-size: 14px;
  block-size: 14px;
}
code {
  padding: 1px 6px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--surface-inset);
  font-size: var(--fs-xs);
}
.table-frame {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
}
.fields-table {
  inline-size: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-sm);
}
.fields-table th,
.fields-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-subtle);
  text-align: start;
  vertical-align: middle;
}
.group-row th,
.group-row td {
  background: var(--surface-inset);
  font-weight: var(--fw-semibold);
}
.group-row th code {
  margin-inline: 6px;
}
.group-row small {
  color: var(--text-tertiary);
  font-weight: 500;
}
.field-row {
  cursor: pointer;
}
.field-row.selected td:first-child {
  box-shadow: inset 3px 0 0 var(--accent-fg);
}
.row-toggle {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin-inline-end: 8px;
  padding: 2px 4px;
  border: 0;
  border-radius: var(--radius-control);
  background: none;
  color: var(--text-primary);
  font: inherit;
  font-weight: var(--fw-semibold);
  text-align: start;
  cursor: pointer;
}
.row-toggle:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.chevron {
  display: inline-block;
  color: var(--text-tertiary);
  transition: rotate var(--motion-fast) var(--ease-standard);
}
.chevron.open {
  rotate: 90deg;
}
.chip {
  display: inline-block;
  margin: 1px 4px 1px 0;
  padding: 2px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.chip.is-policy {
  background: var(--surface-selected);
  color: var(--accent-fg);
}
.actions-col {
  inline-size: 1%;
  white-space: nowrap;
  text-align: end;
}
.actions-col :deep(.flip svg) {
  rotate: 180deg;
}
.empty-row td {
  color: var(--text-tertiary);
}
.detail-row > td {
  padding: 14px 16px 18px;
  background: var(--surface-page);
}
@media (max-width: 820px) {
  .locked-core {
    margin: 0;
  }
}
</style>

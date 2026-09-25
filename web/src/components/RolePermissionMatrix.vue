<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { CapabilityDefinition } from "../api/auth";
import {
  capabilityHelpKey,
  capabilityLabelKey,
  categoryLabelKey,
  groupCapabilities,
  matchesCapabilityFilter,
} from "../domain/roles";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

const props = defineProps<{
  capabilities: CapabilityDefinition[];
  modelValue: string[];
  disabled?: boolean;
  filter?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();
const i18n = useI18nStore();
const selected = computed(() => new Set(props.modelValue));
const visible = computed(() =>
  props.capabilities.filter((item) =>
    matchesCapabilityFilter(
      {
        id: item.id,
        label: i18n.t(capabilityLabelKey(item.id), item.label),
        description: i18n.t(capabilityHelpKey(item.id), item.description),
      },
      props.filter || "",
    ),
  ),
);
const groups = computed(() => groupCapabilities(visible.value));

function toggle(id: string, checked: boolean) {
  if (props.disabled) return;
  const next = new Set(props.modelValue);
  if (checked) next.add(id);
  else next.delete(id);
  emit("update:modelValue", [...next]);
}

function configurableIds(items: CapabilityDefinition[]) {
  return items.filter((item) => item.configurable).map((item) => item.id);
}

function groupComplete(items: CapabilityDefinition[]) {
  const ids = configurableIds(items);
  return ids.length > 0 && ids.every((id) => selected.value.has(id));
}

function toggleGroup(items: CapabilityDefinition[]) {
  if (props.disabled) return;
  const ids = configurableIds(items);
  if (!ids.length) return;
  const next = new Set(props.modelValue);
  if (groupComplete(items)) ids.forEach((id) => next.delete(id));
  else ids.forEach((id) => next.add(id));
  emit("update:modelValue", [...next]);
}

function enabledCount(items: CapabilityDefinition[]) {
  return items.filter((item) => selected.value.has(item.id)).length;
}

function describedBy(id: string) {
  return `permission-${id.replaceAll(".", "-")}`;
}
</script>

<template>
  <div class="permission-matrix">
    <p v-if="!groups.length" class="permission-empty" role="status">
      {{ i18n.t("roles.filter_empty") }}
    </p>
    <fieldset v-for="group in groups" :key="group.category" class="permission-group">
      <legend class="permission-legend">
        <span class="permission-legend-copy">
          <span>{{ i18n.t(categoryLabelKey(group.category), group.category) }}</span>
          <span class="permission-legend-count">{{
            i18n.tf("roles.category_count", {
              enabled: enabledCount(group.items),
              total: group.items.length,
            })
          }}</span>
        </span>
        <UiButton
          v-if="!disabled && configurableIds(group.items).length"
          size="small"
          variant="ghost"
          :label="
            groupComplete(group.items)
              ? i18n.tf('roles.category_none', {
                  category: i18n.t(categoryLabelKey(group.category), group.category),
                })
              : i18n.tf('roles.category_all', {
                  category: i18n.t(categoryLabelKey(group.category), group.category),
                })
          "
          @click="toggleGroup(group.items)"
        />
      </legend>
      <label
        v-for="capability in group.items"
        :key="capability.id"
        class="permission-row"
        :class="{ locked: disabled || !capability.configurable }"
      >
        <input
          type="checkbox"
          :checked="selected.has(capability.id)"
          :disabled="disabled || !capability.configurable"
          :aria-describedby="describedBy(capability.id)"
          @change="toggle(capability.id, ($event.target as HTMLInputElement).checked)"
        />
        <span class="permission-copy">
          <span class="permission-title">
            <b>{{ i18n.t(capabilityLabelKey(capability.id), capability.label) }}</b>
            <UiStatusBadge
              v-if="!capability.configurable"
              :label="i18n.t('roles.admin_only')"
              tone="warning"
              :help="i18n.t('roles.admin_locked_help')"
            />
          </span>
          <small :id="describedBy(capability.id)">{{
            i18n.t(capabilityHelpKey(capability.id), capability.description)
          }}</small>
          <code :title="i18n.t('roles.permission_id')">{{ capability.id }}</code>
        </span>
      </label>
    </fieldset>
  </div>
</template>

<style scoped>
.permission-matrix {
  display: grid;
  gap: 12px;
}
.permission-empty {
  margin: 0;
  padding: 18px 4px;
  color: var(--muted);
  font-size: 0.875rem;
}
.permission-group {
  margin: 0;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  display: grid;
  gap: 4px;
}
.permission-legend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px 6px;
  font-size: 0.8125rem;
  font-weight: 800;
  color: var(--text-2);
}
.permission-legend-copy {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.permission-legend-count {
  font-weight: 650;
  color: var(--muted);
}
.permission-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  min-height: 52px;
  margin: 0 8px 8px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.permission-row:hover {
  background: var(--panel-2);
  border-color: var(--line);
}
.permission-row.locked {
  cursor: not-allowed;
  color: var(--muted);
}
.permission-row input {
  margin-top: 4px;
  width: 17px;
  height: 17px;
  accent-color: var(--ui-accent);
}
.permission-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.permission-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.permission-row b {
  font-size: 0.875rem;
  color: var(--text);
}
.permission-row.locked b {
  color: var(--muted);
}
.permission-row small {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
.permission-row code {
  width: fit-content;
  margin-top: 2px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--soft);
  font-size: 0.8125rem;
  color: var(--muted);
}
.permission-row:focus-within {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
@media (max-width: 640px) {
  .permission-legend {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

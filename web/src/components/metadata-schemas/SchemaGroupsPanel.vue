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
import { computed, ref, watch } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import { CORE_GROUP, type MetadataSchema, type SchemaGroup } from "../../api/metadataSchemas";
import UiButton from "../ui/UiButton.vue";
import UiField from "../ui/UiField.vue";
import UiInput from "../ui/UiInput.vue";
import UiSelect from "../ui/UiSelect.vue";
import UiTextarea from "../ui/UiTextarea.vue";

// The prompt each group sends: one group is one model call per record. Edited one group at a time so the
// page stays short however many groups a schema has.
const props = defineProps<{ draft: MetadataSchema; readonly: boolean }>();
const { t, tf } = useSchemaCopy();

const selectedKey = ref(props.draft.groups[0]?.key ?? "");
const group = computed(() => props.draft.groups.find((g) => g.key === selectedKey.value));
const fieldCount = computed(
  () => props.draft.fields.filter((f) => f.group === selectedKey.value).length,
);
// A different schema (or a removed group) can leave the selection pointing nowhere.
watch(
  () => props.draft.groups.map((g) => g.key).join("\n"),
  () => {
    if (!group.value) selectedKey.value = props.draft.groups[0]?.key ?? "";
  },
);

const notesText = (g: SchemaGroup) => g.notes.join("\n");
function setNotes(g: SchemaGroup, text: string) {
  g.notes = text
    .split("\n")
    .map((n) => n.trim())
    .filter(Boolean);
}
function addGroup() {
  const n = props.draft.groups.length + 1;
  props.draft.groups.push({
    key: `group_${n}`,
    label: tf("new_group_name", { number: n }),
    intro: "Infer ONLY the following metadata for one immutable DerridAI record.",
    fields_heading: "",
    notes: [],
    trailer: "",
    footer:
      "Return one field_assessments entry for every one of {assessed_fields}. Each assessment must contain confidence (0..1 or null), needs_review, reason, and outcome (supported_value, no_supported_value, or uncertain).\n",
  });
  selectedKey.value = `group_${n}`;
}
function removeGroup() {
  const key = selectedKey.value;
  if (key === CORE_GROUP) return;
  props.draft.groups = props.draft.groups.filter((g) => g.key !== key);
  props.draft.fields = props.draft.fields.filter((f) => f.group !== key);
}
</script>

<template>
  <!-- eslint-disable vue/no-mutating-props -->
  <div class="groups-panel">
    <div class="panel-toolbar">
      <UiField :label="t('preview_group', 'Group')" control-id="schema-group-picker">
        <UiSelect id="schema-group-picker" v-model="selectedKey">
          <option v-for="g in draft.groups" :key="g.key" :value="g.key">{{ g.label }}</option>
        </UiSelect>
      </UiField>
      <p class="hint">{{ t("group_help", "Each group is one model call per record.") }}</p>
      <span class="spacer"></span>
      <UiButton
        size="small"
        icon="plus"
        :disabled="readonly"
        :label="t('add_group', 'Add a group')"
        @click="addGroup"
      />
    </div>

    <p v-if="!group" class="hint">{{ t("no_groups", "This schema has no groups.") }}</p>
    <section v-else class="group-form" :aria-label="group.label">
      <div class="group-head">
        <h3>
          {{ group.label }}
          <small>{{ tf("group_fields", { count: fieldCount }) }}</small>
        </h3>
        <UiButton
          v-if="group.key !== CORE_GROUP"
          variant="danger"
          size="small"
          icon="trash"
          :disabled="readonly"
          :label="t('remove_group', 'Remove group')"
          @click="removeGroup"
        />
        <small v-else class="hint">{{ t("holds_core", "holds the locked core") }}</small>
      </div>
      <fieldset class="group-fields" :disabled="readonly">
        <UiField :label="t('group_label', 'Group name')" control-id="schema-group-name">
          <UiInput id="schema-group-name" v-model="group.label" maxlength="80" />
        </UiField>
        <UiField
          :label="t('fields_heading', 'Heading above the field list')"
          control-id="schema-group-fields-heading"
        >
          <UiInput id="schema-group-fields-heading" v-model="group.fields_heading" />
        </UiField>
        <UiField
          :label="t('intro', 'Opening instructions')"
          control-id="schema-group-intro"
          wide
        >
          <UiTextarea id="schema-group-intro" v-model="group.intro" rows="4" />
        </UiField>
        <UiField
          :label="t('notes', 'Notes after the field list (one per line)')"
          control-id="schema-group-notes"
          wide
        >
          <UiTextarea
            id="schema-group-notes"
            :model-value="notesText(group)"
            rows="3"
            @update:model-value="setNotes(group, String($event ?? ''))"
          />
        </UiField>
        <UiField :label="t('trailer', 'Closing remarks')" control-id="schema-group-trailer">
          <UiTextarea id="schema-group-trailer" v-model="group.trailer" rows="3" />
        </UiField>
        <UiField
          :label="t('footer', 'Evidence and confidence instructions')"
          :hint="t('footer_help')"
          control-id="schema-group-footer"
        >
          <template #default="{ describedby, invalid }">
            <UiTextarea
              id="schema-group-footer"
              v-model="group.footer"
              rows="3"
              :aria-describedby="describedby"
              :invalid="invalid"
            />
          </template>
        </UiField>
      </fieldset>
    </section>
  </div>
</template>

<style scoped>
.groups-panel {
  display: grid;
  gap: 12px;
}
.panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  align-items: end;
}
.spacer {
  flex: 1;
}
.group-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
}
.group-head {
  grid-column: 1 / -1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.group-head h3 {
  margin: 0;
  font-size: 1rem;
}
.group-head h3 small,
.hint {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-weight: 500;
}
.hint {
  margin: 0;
}
.group-fields {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  border: 0;
  min-inline-size: 0;
}
@media (max-width: 820px) {
  .group-form,
  .group-fields {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

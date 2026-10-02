<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/* eslint-disable vue/no-mutating-props -- the parent hands over its draft on purpose; these components edit it in place and the parent tracks dirtiness by comparing the whole draft. */
import { computed, ref, watch } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import { CORE_GROUP, type MetadataSchema, type SchemaGroup } from "../../api/metadataSchemas";
import UiButton from "../ui/UiButton.vue";

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
    label: `Group ${n}`,
    intro: "Infer ONLY the following metadata for one immutable DerridAI record.",
    fields_heading: "",
    notes: [],
    trailer: "",
    footer:
      "Return one field_assessments entry for every one of {assessed_fields}. Each assessment must contain confidence (0..1 or null), needs_review, reason, and outcome (supported_value, no_supported_value, or uncertain).\n",
    repeatable: false,
    max_items: null,
    instance_label: "{label} {number}",
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
      <label class="group-pick">
        <span>{{ t("preview_group", "Group") }}</span>
        <select v-model="selectedKey" class="control">
          <option v-for="g in draft.groups" :key="g.key" :value="g.key">{{ g.label }}</option>
        </select>
      </label>
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
      <label class="schema-field"
        ><span>{{ t("group_label", "Group name") }}</span
        ><input v-model="group.label" class="control" maxlength="80"
      /></label>
      <label class="schema-field"
        ><span>{{ t("fields_heading", "Heading above the field list") }}</span
        ><input v-model="group.fields_heading" class="control"
      /></label>
      <label v-if="group.key !== CORE_GROUP" class="schema-field checkbox-field">
        <input
          v-model="group.repeatable"
          type="checkbox"
          :disabled="readonly"
          @change="group.max_items = group.repeatable ? group.max_items || 8 : null"
        />
        <span>{{ t("repeatable_group", "Repeat associated field set") }}</span>
      </label>
      <label v-if="group.repeatable" class="schema-field"
        ><span>{{ t("repeatable_max_items", "Maximum instances") }}</span
        ><input v-model.number="group.max_items" class="control" type="number" min="1" max="24"
      /></label>
      <label v-if="group.repeatable" class="schema-field"
        ><span>{{ t("repeatable_instance_label", "Instance label pattern") }}</span
        ><input
          v-model="group.instance_label"
          class="control"
          maxlength="120"
          placeholder="{label} {number}"
        /><small class="hint">{label} · {number}</small></label
      >
      <label class="schema-field wide"
        ><span>{{ t("intro", "Opening instructions") }}</span
        ><textarea v-model="group.intro" class="control" rows="4"></textarea>
      </label>
      <label class="schema-field wide"
        ><span>{{ t("notes", "Notes after the field list (one per line)") }}</span
        ><textarea
          :value="notesText(group)"
          class="control"
          rows="3"
          @input="setNotes(group, ($event.target as HTMLTextAreaElement).value)"
        ></textarea>
      </label>
      <label class="schema-field"
        ><span>{{ t("trailer", "Closing remarks") }}</span
        ><textarea v-model="group.trailer" class="control" rows="3"></textarea>
      </label>
      <label class="schema-field"
        ><span>{{ t("footer", "Evidence and confidence instructions") }}</span
        ><textarea v-model="group.footer" class="control" rows="3"></textarea
        ><small class="hint">{{ t("footer_help") }}</small></label
      >
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
.group-pick {
  display: grid;
  gap: 4px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
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
.schema-field {
  display: grid;
  gap: 4px;
  min-inline-size: 0;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.schema-field.wide {
  grid-column: 1 / -1;
}
.checkbox-field {
  grid-template-columns: auto 1fr;
  align-items: center;
  align-self: end;
  min-block-size: 40px;
}
.schema-field :is(input, select, textarea) {
  inline-size: 100%;
  font-weight: 500;
}
.control {
  min-block-size: 40px;
}
@media (max-width: 820px) {
  .group-form {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

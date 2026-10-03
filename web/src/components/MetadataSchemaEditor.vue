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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useSchemaCopy } from "../composables/useSchemaCopy";
import type { ProviderProfile } from "../api/system";
import UiButton from "./ui/UiButton.vue";
import UiField from "./ui/UiField.vue";
import UiInput from "./ui/UiInput.vue";
import UiStatusBadge from "./ui/UiStatusBadge.vue";
import UiTabs from "./ui/UiTabs.vue";
import UiTooltip from "./ui/UiTooltip.vue";
import SchemaFieldsTable from "./metadata-schemas/SchemaFieldsTable.vue";
import SchemaDocumentFieldsPanel from "./metadata-schemas/SchemaDocumentFieldsPanel.vue";
import SchemaGroupsPanel from "./metadata-schemas/SchemaGroupsPanel.vue";
import SchemaListTable from "./metadata-schemas/SchemaListTable.vue";
import SchemaPreviewPanel from "./metadata-schemas/SchemaPreviewPanel.vue";
import {
  completeDocumentFields,
  blankField,
  metadataSchemasApi,
  type MetadataSchema,
  type SchemaSummary,
} from "../api/metadataSchemas";

// Define which metadata fields a corpus record has, what each may hold and what the model is told to look for.
// Three fields (region type, primary text, discourse role) are the locked core: they are in every schema and are
// not edited here. A build copies the schema it starts with, so nothing done here changes a build already made.
// This component owns the draft and every request; the tables and forms below only edit the draft in place.
const props = withDefaults(
  defineProps<{
    providerProfiles?: ProviderProfile[];
    defaultProviderId?: string;
    initialSchemaId?: string;
    initialTab?: string;
  }>(),
  {
    providerProfiles: () => [],
    defaultProviderId: "",
    initialSchemaId: "default",
    initialTab: "fields",
  },
);
const emit = defineEmits<{
  saved: [id: string];
  changed: [];
  selection: [id: string];
  tab: [id: string];
}>();
const { t, tf } = useSchemaCopy();

const VALID_TABS = new Set(["fields", "document", "groups", "preview"]);
const summaries = ref<SchemaSummary[]>([]);
const selectedId = ref(props.initialSchemaId || "default");
const draft = ref<MetadataSchema | null>(null);
const savedHash = ref("");
const error = ref("");
const notice = ref("");
const busy = ref(false);
const isNew = ref(false);
const tab = ref(VALID_TABS.has(props.initialTab) ? props.initialTab : "fields");

const builtin = computed(() => {
  if (isNew.value) return false;
  return summaries.value.some((item) => item.id === selectedId.value && item.builtin);
});
const dirty = computed(() => JSON.stringify(draft.value) !== savedHash.value);
const readonly = computed(() => builtin.value || busy.value);
const tabs = computed(() => [
  { id: "fields", label: t("tab_fields", "Fields") },
  { id: "document", label: t("tab_document_fields", "Document fields") },
  { id: "groups", label: t("tab_prompts", "Prompt groups") },
  { id: "preview", label: t("tab_preview", "Test schema") },
]);

function load(schema: MetadataSchema, fresh = false) {
  const next = JSON.parse(JSON.stringify(schema)) as MetadataSchema;
  for (const field of next.fields) {
    field.retrieval_profile ||= blankField().retrieval_profile;
    field.pos_tags ||= [];
    field.ner_tags ||= [];
    field.scope ||= "record";
    field.members ||= [];
    field.max_items = field.type === "repeatable" ? field.max_items || 8 : null;
    field.instance_label ||= "{label} {number}";
  }
  next.document_fields = completeDocumentFields(next.document_fields);
  draft.value = next;
  savedHash.value = JSON.stringify(draft.value);
  isNew.value = fresh;
  error.value = "";
}
const confirmDiscard = () =>
  !dirty.value || window.confirm(t("discard_changes", "Discard unsaved schema changes?"));
async function refresh(keep?: string) {
  summaries.value = (await metadataSchemasApi.list()).items;
  const id = keep && summaries.value.some((s) => s.id === keep) ? keep : selectedId.value;
  await select(summaries.value.some((s) => s.id === id) ? id : "default", true);
}
async function select(id: string, force = false) {
  if (!force && id === selectedId.value && !isNew.value) return;
  if (!force && !confirmDiscard()) {
    emit("selection", selectedId.value);
    return;
  }
  selectedId.value = id;
  notice.value = "";
  load(await metadataSchemasApi.get(id));
  emit("selection", id);
}
async function guarded<T>(work: () => Promise<T>): Promise<T | undefined> {
  busy.value = true;
  error.value = "";
  try {
    return await work();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
    return undefined;
  } finally {
    busy.value = false;
  }
}
/** A new schema starts from the built-in groups and prompts with no added fields (the core stays). */
async function newSchema() {
  if (!confirmDiscard()) return;
  const base = await guarded(() => metadataSchemasApi.get("default"));
  if (!base) return;
  load(
    {
      ...JSON.parse(JSON.stringify(base)),
      id: "",
      name: t("new_schema_name", "New schema"),
      fields: [],
    },
    true,
  );
  savedHash.value = "";
  // Unsaved drafts are deliberately transient. Keep the URL bound to the last
  // durable schema until this draft is saved.
  selectedId.value = "";
  tab.value = "fields";
}
function duplicate() {
  if (!draft.value) return;
  load(
    {
      ...JSON.parse(JSON.stringify(draft.value)),
      id: "",
      name: tf("copy_name", { name: draft.value.name }),
    },
    true,
  );
  savedHash.value = ""; // a copy is unsaved
  // Do not put unsaved draft identity into the shareable route.
  selectedId.value = "";
}
async function save() {
  const schema = draft.value;
  if (!schema || builtin.value || busy.value || (!dirty.value && !isNew.value)) return;
  const saved = await guarded(() =>
    isNew.value
      ? metadataSchemasApi.create(schema)
      : metadataSchemasApi.update(selectedId.value, schema),
  );
  if (!saved) return;
  notice.value = t("saved", "Schema saved.");
  await refresh(saved.id);
  emit("saved", saved.id);
  emit("changed");
}
async function remove() {
  if (
    builtin.value ||
    isNew.value ||
    !window.confirm(
      t("delete_confirm", "Delete this schema? Builds that already used it keep their own copy."),
    )
  )
    return;
  if (await guarded(() => metadataSchemasApi.remove(selectedId.value))) {
    selectedId.value = "default";
    await refresh("default");
    emit("changed");
  }
}
async function exportFile() {
  const payload = await guarded(() => metadataSchemasApi.exportFile(selectedId.value));
  if (!payload) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(payload, null, 1)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `${selectedId.value}.derridai-schema.json`;
  link.click();
  URL.revokeObjectURL(url);
}
async function importFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  (event.target as HTMLInputElement).value = "";
  if (!file) return;
  let payload: unknown;
  try {
    payload = JSON.parse(await file.text());
  } catch {
    error.value = t("import_not_json", "That file is not JSON.");
    return;
  }
  const imported = await guarded(() => metadataSchemasApi.importFile(payload));
  if (imported) {
    notice.value = t("imported", "Schema imported.");
    await refresh(imported.id);
    emit("changed");
  }
}
const runPreview = (payload: Record<string, unknown>) =>
  guarded(() => metadataSchemasApi.preview(payload));

// Ctrl/Cmd+S saves, and leaving the page with unsaved edits asks first.
function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    void save();
  }
}
function onBeforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value && !builtin.value) event.preventDefault();
}
watch(tab, (id) => emit("tab", id));
watch(
  () => props.initialSchemaId,
  (value) => {
    const id = value || "default";
    if (id === selectedId.value || !summaries.value.length) return;
    void select(summaries.value.some((item) => item.id === id) ? id : "default");
  },
);
watch(
  () => props.initialTab,
  (value) => {
    if (VALID_TABS.has(value) && value !== tab.value) tab.value = value;
  },
);

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
  window.addEventListener("beforeunload", onBeforeUnload);
  void refresh();
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener("beforeunload", onBeforeUnload);
});
defineExpose({ select, draft });
</script>

<template>
  <div class="schema-editor">
    <section class="schema-library" :aria-label="t('saved_schemas', 'Saved schemas')">
      <div class="library-bar">
        <h2>{{ t("saved_schemas", "Saved schemas") }}</h2>
        <span class="spacer"></span>
        <label class="import-button btn small">
          <span>{{ t("import", "Import a schema…") }}</span>
          <input type="file" accept="application/json,.json" class="sr-only" @change="importFile" />
        </label>
        <UiButton
          variant="primary"
          size="small"
          icon="plus"
          button-class="new-schema"
          :disabled="busy"
          :label="t('new_schema', 'New schema')"
          @click="newSchema"
        />
      </div>
      <SchemaListTable
        :items="summaries"
        :selected-id="selectedId"
        :unsaved-name="isNew ? draft?.name || t('new_schema_name', 'New schema') : ''"
        @select="select($event)"
      />
    </section>

    <section v-if="draft" class="schema-form" :aria-label="t('editor', 'Schema editor')">
      <p v-if="error" class="schema-error" role="alert">{{ error }}</p>
      <p v-if="notice" class="schema-notice" role="status">{{ notice }}</p>
      <p v-if="builtin" class="schema-note">
        {{ t("builtin_help") }}
      </p>

      <header class="schema-bar">
        <div class="schema-context">
          <span>{{ t("editing_schema", "Editing schema") }}</span>
          <strong>{{ draft.name }}</strong>
        </div>
        <div class="schema-status">
          <UiStatusBadge v-if="builtin" tone="info" :label="t('builtin', 'Built in')" />
          <UiStatusBadge v-else-if="isNew" tone="warning" :label="t('unsaved', 'Not saved yet')" />
          <UiStatusBadge
            v-else-if="dirty"
            tone="warning"
            :label="t('unsaved_changes', 'Unsaved changes')"
          />
          <UiStatusBadge v-else tone="success" :label="t('saved_state', 'Saved')" />
          <UiTooltip :text="t('version_help')" trigger-mode="content" placement="bottom">
            <span class="schema-version">
              {{ t("version", "Schema version") }}: <b>v{{ draft.schema_version || "1.0.0" }}</b>
            </span>
          </UiTooltip>
        </div>
        <div class="schema-actions">
          <UiButton
            icon="copy"
            :label="t('duplicate', 'Duplicate')"
            :disabled="busy"
            @click="duplicate"
          />
          <UiButton
            icon="download"
            :label="t('export', 'Export')"
            :disabled="busy || isNew"
            @click="exportFile"
          />
          <UiButton
            icon="trash"
            :label="t('delete', 'Delete')"
            :disabled="busy || builtin || isNew"
            @click="remove"
          />
          <UiButton
            variant="primary"
            :label="t('save', 'Save schema')"
            :disabled="busy || builtin || !dirty"
            @click="save"
          />
        </div>
      </header>

      <fieldset :disabled="readonly" class="schema-identity">
        <UiField :label="t('name', 'Name')" control-id="schema-name">
          <UiInput id="schema-name" v-model="draft.name" maxlength="80" />
        </UiField>
        <UiField :label="t('description', 'Description')" control-id="schema-description">
          <UiInput id="schema-description" v-model="draft.description" maxlength="600" />
        </UiField>
      </fieldset>

      <UiTabs
        v-model="tab"
        :tabs="tabs"
        :tablist-label="t('editor', 'Schema editor')"
        id-prefix="schema"
      />
      <div
        :id="`schema-panel-${tab}`"
        role="tabpanel"
        :aria-labelledby="`schema-tab-${tab}`"
        class="schema-panel"
      >
        <SchemaFieldsTable
          v-if="tab === 'fields'"
          :draft="draft"
          :readonly="readonly"
        />
        <SchemaDocumentFieldsPanel
          v-else-if="tab === 'document'"
          :draft="draft"
          :readonly="readonly"
        />
        <SchemaGroupsPanel
          v-else-if="tab === 'groups'"
          :draft="draft"
          :readonly="readonly"
        />
        <SchemaPreviewPanel
          v-else
          :draft="draft"
          :busy="busy"
          :provider-profiles="props.providerProfiles"
          :default-provider-id="props.defaultProviderId"
          :run="runPreview"
          @manage="emit('changed')"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.schema-editor {
  display: grid;
  grid-template-columns: minmax(16rem, 20rem) minmax(0, 1fr);
  gap: var(--space-5);
  align-content: start;
  align-items: start;
}
.schema-library {
  position: sticky;
  inset-block-start: var(--space-3);
  display: grid;
  gap: var(--space-2);
  min-inline-size: 0;
}
.library-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.library-bar h2 {
  flex-basis: 100%;
  margin: 0;
  font-size: var(--fs-md);
}
.spacer {
  flex: 1;
}
.import-button:focus-within {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.schema-form {
  display: grid;
  gap: var(--space-3);
  min-inline-size: 0;
}
.schema-bar {
  position: sticky;
  inset-block-start: 0;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-raised);
}
.schema-context {
  display: grid;
  gap: var(--space-1);
  min-inline-size: min(22rem, 100%);
}
.schema-context span {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.schema-context strong {
  overflow: hidden;
  color: var(--text-primary);
  font-size: var(--fs-md);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.schema-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
}
.schema-version {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.schema-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.schema-identity {
  margin: 0;
  padding: 0;
  border: 0;
  min-inline-size: 0;
}
.schema-identity {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(0, 2fr);
  gap: 10px 12px;
}
.schema-panel {
  min-inline-size: 0;
}
.schema-error {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--tone-danger-border);
  border-radius: var(--radius-control);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.schema-notice,
.schema-note {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--tone-info-border);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: 0.875rem;
}
@media (max-width: 1100px) {
  .schema-editor {
    grid-template-columns: minmax(0, 1fr);
  }
  .schema-library {
    position: static;
  }
}
@media (max-width: 820px) {
  .schema-identity {
    grid-template-columns: minmax(0, 1fr);
  }
  .schema-bar {
    position: static;
  }
}
</style>

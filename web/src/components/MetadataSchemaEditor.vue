<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
import {
  CORE_FIELDS,
  CORE_GROUP,
  blankField,
  metadataSchemasApi,
  type MetadataSchema,
  type SchemaField,
  type SchemaGroup,
  type SchemaPreview,
  type SchemaSummary,
} from "../api/metadataSchemas";

// Define which metadata fields a corpus record has, what each may hold and what the model is told to look for.
// Three fields (region type, primary text, discourse role) are the locked core: they are in every schema and are
// not edited here. A build copies the schema it starts with, so nothing done here changes a build already made.
type PreviewProfile = {
  id: string;
  name?: string;
  model?: string;
  type?: string;
  base_url?: string;
  api_key?: string;
};
const props = withDefaults(
  defineProps<{ providerProfiles?: PreviewProfile[]; defaultProviderId?: string }>(),
  { providerProfiles: () => [], defaultProviderId: "" },
);
const emit = defineEmits<{ saved: [id: string]; changed: [] }>();
const i18n = useI18nStore();

const summaries = ref<SchemaSummary[]>([]);
const selectedId = ref("default");
const draft = ref<MetadataSchema | null>(null);
const savedHash = ref("");
const error = ref("");
const notice = ref("");
const busy = ref(false);
const isNew = ref(false);

const builtin = computed(() => selectedId.value === "default" && !isNew.value);
const dirty = computed(() => JSON.stringify(draft.value) !== savedHash.value);
const t = (key: string, fallback: string) => i18n.t(`schemas.${key}`, fallback);

function load(schema: MetadataSchema, fresh = false) {
  draft.value = JSON.parse(JSON.stringify(schema));
  savedHash.value = JSON.stringify(draft.value);
  isNew.value = fresh;
  error.value = "";
}
async function refresh(keep?: string) {
  summaries.value = (await metadataSchemasApi.list()).items;
  const id = keep && summaries.value.some((s) => s.id === keep) ? keep : selectedId.value;
  await select(summaries.value.some((s) => s.id === id) ? id : "default");
}
async function select(id: string) {
  selectedId.value = id;
  notice.value = "";
  load(await metadataSchemasApi.get(id));
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
function duplicate() {
  if (!draft.value) return;
  load(
    { ...JSON.parse(JSON.stringify(draft.value)), id: "", name: `${draft.value.name} (copy)` },
    true,
  );
  savedHash.value = ""; // a copy is unsaved
  selectedId.value = "";
}
async function save() {
  const schema = draft.value;
  if (!schema) return;
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

// ---- editing ---------------------------------------------------------------------------------------------------
const groupKeys = computed(() => (draft.value?.groups ?? []).map((g) => g.key));
function addField(group: string) {
  draft.value?.fields.push(blankField(group));
}
function removeField(index: number) {
  draft.value?.fields.splice(index, 1);
}
function moveField(index: number, by: -1 | 1) {
  const fields = draft.value?.fields;
  if (!fields || index + by < 0 || index + by >= fields.length) return;
  [fields[index], fields[index + by]] = [fields[index + by], fields[index]];
}
function addGroup() {
  const n = (draft.value?.groups.length ?? 0) + 1;
  draft.value?.groups.push({
    key: `group_${n}`,
    label: `Group ${n}`,
    intro: "Infer ONLY the following metadata for one immutable DerridAI record.",
    fields_heading: "",
    notes: [],
    trailer: "",
    footer:
      "Return one field_assessments entry for every one of {assessed_fields}. Each assessment must contain confidence (0..1 or null), needs_review, reason, and outcome (supported_value, no_supported_value, or uncertain).\n",
  });
}
function removeGroup(key: string) {
  if (!draft.value || key === CORE_GROUP) return;
  draft.value.groups = draft.value.groups.filter((g) => g.key !== key);
  draft.value.fields = draft.value.fields.filter((f) => f.group !== key);
}
const notesText = (group: SchemaGroup) => group.notes.join("\n");
const setNotes = (group: SchemaGroup, text: string) => {
  group.notes = text
    .split("\n")
    .map((n) => n.trim())
    .filter(Boolean);
};
const fieldsOf = (key: string) =>
  (draft.value?.fields ?? [])
    .map((field, index) => ({ field, index }))
    .filter((item) => item.field.group === key);
const addValue = (field: SchemaField) => field.values.push({ value: "", definition: "" });

// ---- preview ---------------------------------------------------------------------------------------------------
const previewGroup = ref(CORE_GROUP);
const previewText = ref(
  "In this passage Derrida distinguishes the archive from simple memory. He cites Freud while qualifying the claim: the archive is not merely a storehouse, and its authority depends on the institution that preserves and interprets it. The paragraph asks whether a supposedly universal concept can remain neutral when its exclusions and historical conditions are ignored.",
);
const previewProfile = ref("");
const preview = ref<SchemaPreview | null>(null);
function previewProvider(profileId: string): Record<string, unknown> {
  const profile = props.providerProfiles.find((item) => item.id === profileId);
  if (!profile) return { provider_profile_id: profileId };
  const apiKey = profile.api_key?.trim() || "";
  return {
    provider_profile_id: profile.id,
    provider: profile.type,
    model: profile.model,
    base_url: profile.base_url || undefined,
    // The OpenAI key lives on the browser profile. Leave it off when this profile
    // has none, so a key stored for a published profile can still be used.
    api_key: apiKey || undefined,
  };
}
async function tryGroup(run: boolean) {
  const schema = draft.value;
  if (!schema || !previewText.value.trim()) return;
  const payload: Record<string, unknown> = {
    schema,
    group: previewGroup.value,
    text: previewText.value,
    run,
  };
  const profileId =
    previewProfile.value || props.defaultProviderId || props.providerProfiles[0]?.id;
  if (run && profileId) Object.assign(payload, previewProvider(profileId));
  const result = await guarded(() => metadataSchemasApi.preview(payload));
  if (result) preview.value = result;
}

onMounted(() => {
  void refresh();
});
watch(
  () => props.providerProfiles,
  (profiles) => {
    if (!profiles.length) return;
    if (previewProfile.value && !profiles.some((profile) => profile.id === previewProfile.value))
      previewProfile.value = "";
    if (!previewProfile.value && !props.defaultProviderId)
      previewProfile.value = profiles[0]?.id || "";
  },
  { immediate: true, deep: true },
);
defineExpose({ select, draft });
</script>

<template>
  <div class="schema-editor">
    <aside class="schema-list" :aria-label="t('saved_schemas', 'Saved schemas')">
      <ul>
        <li v-for="item in summaries" :key="item.id">
          <button
            type="button"
            class="schema-row"
            :aria-current="item.id === selectedId && !isNew ? 'true' : undefined"
            @click="select(item.id)"
          >
            <b>{{ item.name }}</b>
            <small
              >{{ item.builtin ? t("builtin", "Built in") : "" }} · v{{
                item.schema_version || "1.0.0"
              }}
              ·
              {{
                i18n.tf("schemas.field_count", "{count} fields", { count: item.field_count })
              }}</small
            >
          </button>
        </li>
        <li v-if="isNew" class="schema-row is-new" aria-current="true">
          <b>{{ draft?.name }}</b
          ><small>{{ t("unsaved", "Not saved yet") }}</small>
        </li>
      </ul>
      <label class="import-button btn small"
        >{{ t("import", "Import a schema…")
        }}<input type="file" accept="application/json,.json" class="sr-only" @change="importFile"
      /></label>
    </aside>

    <section v-if="draft" class="schema-form" :aria-label="t('editor', 'Schema editor')">
      <p v-if="error" class="schema-error" role="alert">{{ error }}</p>
      <p v-if="notice" class="schema-notice" role="status">{{ notice }}</p>
      <p v-if="builtin" class="schema-note">
        {{
          t(
            "builtin_help",
            "The built-in schema describes the fields DerridAI has always produced. It cannot be changed; duplicate it to make your own.",
          )
        }}
      </p>

      <div class="schema-actions">
        <UiButton :label="t('duplicate', 'Duplicate')" :disabled="busy" @click="duplicate" />
        <UiButton :label="t('export', 'Export')" :disabled="busy || isNew" @click="exportFile" />
        <UiButton
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

      <fieldset :disabled="builtin || busy" class="schema-fieldset">
        <label class="schema-field"
          ><span>{{ t("name", "Name") }}</span
          ><input v-model="draft.name" class="control" maxlength="80"
        /></label>
        <p class="schema-version">
          {{ t("version", "Schema version") }}: <b>v{{ draft.schema_version || "1.0.0" }}</b
          ><span>{{
            t("version_help", "Versions change automatically when the saved schema changes.")
          }}</span>
        </p>
        <label class="schema-field"
          ><span>{{ t("description", "Description") }}</span
          ><textarea
            v-model="draft.description"
            class="control"
            rows="2"
            maxlength="600"
          ></textarea>
        </label>

        <div class="locked-core" role="note">
          <b>{{ t("locked_core", "Locked core") }}</b>
          <span>{{
            t(
              "locked_core_help",
              "Every schema has these three fields. DerridAI's page and layout logic depends on them, so they cannot be changed or removed.",
            )
          }}</span>
          <code v-for="name in CORE_FIELDS" :key="name">{{ name }}</code>
        </div>

        <section
          v-for="group in draft.groups"
          :key="group.key"
          class="schema-group"
          :aria-labelledby="`group-${group.key}`"
        >
          <header>
            <h3 :id="`group-${group.key}`">
              {{ group.label }}
              <small>{{
                group.key === CORE_GROUP ? t("holds_core", "holds the locked core") : ""
              }}</small>
            </h3>
            <button
              v-if="group.key !== CORE_GROUP"
              type="button"
              class="link-button"
              @click="removeGroup(group.key)"
            >
              {{ t("remove_group", "Remove group") }}
            </button>
          </header>
          <p class="hint">{{ t("group_help", "Each group is one model call per record.") }}</p>
          <label class="schema-field"
            ><span>{{ t("group_label", "Group name") }}</span
            ><input v-model="group.label" class="control" maxlength="80"
          /></label>
          <label class="schema-field"
            ><span>{{ t("intro", "Opening instructions") }}</span
            ><textarea v-model="group.intro" class="control" rows="4"></textarea>
          </label>
          <label class="schema-field"
            ><span>{{ t("fields_heading", "Heading above the field list") }}</span
            ><input v-model="group.fields_heading" class="control"
          /></label>
          <label class="schema-field"
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
            ><small class="hint">{{
              t("footer_help", "You can use {fields} and {assessed_fields}.")
            }}</small></label
          >

          <h4>{{ t("fields", "Fields") }}</h4>
          <article v-for="item in fieldsOf(group.key)" :key="item.index" class="schema-field-card">
            <div class="row">
              <label class="schema-field"
                ><span>{{ t("field_name", "Field name") }}</span
                ><input v-model="item.field.name" class="control" maxlength="40" spellcheck="false"
              /></label>
              <label class="schema-field"
                ><span>{{ t("field_label", "Label") }}</span
                ><input v-model="item.field.label" class="control" maxlength="80"
              /></label>
              <label class="schema-field"
                ><span>{{ t("field_type", "Type") }}</span>
                <select v-model="item.field.type" class="control">
                  <option value="text">{{ t("type_text", "Text") }}</option>
                  <option value="number">{{ t("type_number", "Number") }}</option>
                  <option value="boolean">{{ t("type_boolean", "Yes / no") }}</option>
                  <option value="choice">{{ t("type_choice", "One of a list") }}</option>
                  <option value="list">{{ t("type_list", "List of texts") }}</option>
                </select></label
              >
              <label class="schema-field"
                ><span>{{ t("field_group", "Group") }}</span
                ><select v-model="item.field.group" class="control">
                  <option v-for="key in groupKeys" :key="key" :value="key">{{ key }}</option>
                </select></label
              >
            </div>
            <label class="schema-field"
              ><span>{{ t("instruction", "What the model should look for") }}</span
              ><textarea v-model="item.field.instruction" class="control" rows="2"></textarea
              ><small class="hint">{{
                t(
                  "instruction_help",
                  "Shown to the model after the field's name. {values} is replaced by the allowed values.",
                )
              }}</small></label
            >
            <div v-if="item.field.type === 'choice'" class="values">
              <div v-for="(value, vi) in item.field.values" :key="vi" class="value-row">
                <input
                  v-model="value.value"
                  class="control"
                  :aria-label="t('value', 'Allowed value')"
                  maxlength="80"
                />
                <input
                  v-model="value.definition"
                  class="control"
                  :aria-label="t('definition', 'What it means (optional)')"
                  :placeholder="t('definition', 'What it means (optional)')"
                />
                <button type="button" class="link-button" @click="item.field.values.splice(vi, 1)">
                  {{ t("remove", "Remove") }}
                </button>
              </div>
              <button type="button" class="btn small" @click="addValue(item.field)">
                {{ t("add_value", "Add a value") }}
              </button>
              <label class="check"
                ><input v-model="item.field.strict" type="checkbox" /><span>{{
                  t("strict", "The model may only return these values")
                }}</span></label
              >
            </div>
            <div class="flags">
              <label class="check"
                ><input v-model="item.field.evidence" type="checkbox" /><span>{{
                  t("evidence", "Must cite the source")
                }}</span></label
              >
              <label class="check"
                ><input v-model="item.field.assess" type="checkbox" /><span>{{
                  t("assess", "Report its confidence")
                }}</span></label
              >
              <label class="check"
                ><input v-model="item.field.review" type="checkbox" /><span>{{
                  t("review", "A person must settle it before accepting")
                }}</span></label
              >
              <span class="grow"></span>
              <button
                type="button"
                class="link-button"
                :disabled="builtin"
                @click="moveField(item.index, -1)"
              >
                {{ t("up", "Move up") }}
              </button>
              <button
                type="button"
                class="link-button"
                :disabled="builtin"
                @click="moveField(item.index, 1)"
              >
                {{ t("down", "Move down") }}
              </button>
              <button type="button" class="link-button" @click="removeField(item.index)">
                {{ t("remove_field", "Remove field") }}
              </button>
            </div>
          </article>
          <button type="button" class="btn small" @click="addField(group.key)">
            {{ t("add_field", "Add a field") }}
          </button>
        </section>
        <button type="button" class="btn small" @click="addGroup">
          {{ t("add_group", "Add a group") }}
        </button>
      </fieldset>

      <section class="schema-preview" aria-labelledby="schema-preview-title">
        <h3 id="schema-preview-title">{{ t("preview", "Try it on a passage") }}</h3>
        <p class="hint">
          {{
            t(
              "preview_help",
              "See the prompt a group produces, or run it on a passage with a model. A real build adds the document details and earlier reviewer decisions.",
            )
          }}
        </p>
        <div class="row">
          <label class="schema-field"
            ><span>{{ t("preview_group", "Group") }}</span
            ><select v-model="previewGroup" class="control">
              <option v-for="key in groupKeys" :key="key" :value="key">{{ key }}</option>
            </select></label
          >
        </div>
        <ProviderProfileSelect
          v-if="providerProfiles.length"
          v-model="previewProfile"
          :profiles="providerProfiles"
          :default-profile-id="defaultProviderId"
          :label="t('preview_model', 'Provider profile')"
          :help="t('preview_provider_help', 'Use the same configured profile and credentials as a Corpus Builder run.')"
          :manage-label="t('preview_manage_provider', 'Manage provider profiles')"
          @manage="emit('changed')"
        />
        <label class="schema-field"
          ><span>{{ t("preview_text", "Passage") }}</span
          ><textarea v-model="previewText" class="control" rows="5"></textarea>
        </label>
        <div class="schema-actions">
          <UiButton
            :label="t('show_prompt', 'Show the prompt')"
            :disabled="busy || !previewText.trim()"
            @click="tryGroup(false)"
          /><UiButton
            variant="primary"
            :label="t('run_sample', 'Run on this passage')"
            :disabled="busy || !previewText.trim()"
            @click="tryGroup(true)"
          />
        </div>
        <template v-if="preview">
          <h4>{{ t("prompt", "Prompt") }}</h4>
          <pre class="preview-out" tabindex="0">{{ preview.prompt }}</pre>
          <template v-if="preview.answer !== undefined"
            ><h4>
              {{
                i18n.tf("schemas.answer", "Answer ({seconds} s)", { seconds: preview.seconds ?? 0 })
              }}
            </h4>
            <pre class="preview-out" tabindex="0">{{
              JSON.stringify(preview.answer, null, 1)
            }}</pre>
          </template>
        </template>
      </section>
    </section>
  </div>
</template>

<style scoped>
.schema-editor {
  display: grid;
  grid-template-columns: minmax(12rem, 16rem) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.schema-list ul {
  display: grid;
  gap: 6px;
  margin: 0 0 10px;
  padding: 0;
  list-style: none;
}
.schema-row {
  display: grid;
  gap: 2px;
  inline-size: 100%;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  color: var(--text);
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.schema-row[aria-current="true"] {
  border-color: var(--accent-fg);
  box-shadow: inset 3px 0 0 var(--accent-fg);
}
.schema-row small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.schema-row:focus-visible,
.import-button:focus-within {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.schema-form {
  display: grid;
  gap: 14px;
  min-inline-size: 0;
}
.schema-fieldset {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  border: 0;
  min-inline-size: 0;
}
.schema-fieldset:disabled {
  opacity: 0.85;
}
.schema-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.schema-error {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--tone-danger-border);
  border-radius: 10px;
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.schema-notice,
.schema-note {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--tone-info-border);
  border-radius: 10px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: 0.875rem;
}
.locked-core {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
  background: var(--soft);
  font-size: 0.875rem;
}
.locked-core code,
.schema-group code {
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--card);
  border: 1px solid var(--line);
}
.schema-group {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.schema-group header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
}
.schema-group h3,
.schema-preview h3 {
  margin: 0;
  font-size: 1rem;
}
h4 {
  margin: 4px 0 0;
  font-size: 0.9375rem;
}
.schema-group h3 small {
  color: var(--muted);
  font-weight: 500;
}
.schema-field {
  display: grid;
  gap: 4px;
  font-size: 0.8125rem;
  font-weight: 700;
  min-inline-size: 0;
}
.schema-field textarea,
.schema-field input,
.schema-field select {
  inline-size: 100%;
  font-weight: 500;
}
.hint {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 500;
  margin: 0;
}
.row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 10px;
}
.schema-field-card {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--bg);
}
.values {
  display: grid;
  gap: 6px;
}
.value-row {
  display: grid;
  grid-template-columns: minmax(6rem, 0.5fr) minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}
.flags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  align-items: center;
}
.check {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 0.8125rem;
  font-weight: 500;
}
.grow {
  flex: 1;
}
.link-button {
  border: 0;
  background: none;
  padding: 4px 6px;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 700;
  text-decoration: underline;
  cursor: pointer;
}
.link-button:disabled {
  color: var(--muted);
  cursor: not-allowed;
}
.link-button:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.schema-preview {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
}
.preview-out {
  max-block-size: 22rem;
  overflow: auto;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  font-size: 0.8125rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.preview-out:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.control {
  min-block-size: 40px;
}
@media (max-width: 820px) {
  .schema-editor {
    grid-template-columns: minmax(0, 1fr);
  }
  .value-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

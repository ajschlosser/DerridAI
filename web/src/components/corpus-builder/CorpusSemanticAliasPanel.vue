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
 * Reviewed identities: a reviewer states which surfaces name one person, work or concept.
 *
 * These are canonical reviewer decisions for the build. DerridAI uses them when it decides
 * whether a reviewer's edit restated the model's value, when it groups reviewed precedents,
 * and when it draws the semantic map. Saving a change retires the old set and keeps it in
 * the build's history; nothing here rewrites a Record's metadata.
 */
import { computed, onMounted, ref, useId } from "vue";
import {
  corpusBuildsApi,
  type SemanticAliasKind,
  type SemanticAliasSet,
  type SemanticAliasSource,
} from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiLoadingState from "../ui/UiLoadingState.vue";

const props = defineProps<{
  buildId: string;
  disabled?: boolean;
  /** Shown inside the semantic dialog: always open, no disclosure summary, loads on mount. */
  embedded?: boolean;
}>();
const emit = defineEmits<{ changed: [] }>();
const i18n = useI18nStore();
const t = (key: string, fallback?: string) =>
  i18n.t(`pdf_corpus.semantic_aliases.${key}`, fallback);
const tf = (key: string, values: Record<string, string | number>) =>
  i18n.tf(`pdf_corpus.semantic_aliases.${key}`, values);

const items = ref<SemanticAliasSet[]>([]);
const kinds = ref<SemanticAliasKind[]>([]);
const loaded = ref(false);
const loading = ref(false);
const saving = ref(false);
const loadError = ref("");
const saveError = ref("");
const status = ref("");
const confirmingRetire = ref("");

const kind = ref("");
const canonicalLabel = ref("");
const aliasText = ref("");
const reason = ref("");
const editing = ref<SemanticAliasSet | null>(null);

// Importing another corpus's reviewed identities copies them here, with provenance.
const importing = ref(false);
const importBusy = ref(false);
const importError = ref("");
const importSkipped = ref<string[]>([]);
const sources = ref<SemanticAliasSource[] | null>(null);
const sourceBuildId = ref("");
const sourceItems = ref<SemanticAliasSet[]>([]);
const selectedImports = ref<string[]>([]);

const formId = useId();
const sourceId = `${formId}-source`;
const kindId = `${formId}-kind`;
const labelId = `${formId}-label`;
const aliasesId = `${formId}-aliases`;
const reasonId = `${formId}-reason`;

const grouped = computed(() => {
  const byKind = new Map<string, SemanticAliasSet[]>();
  for (const item of items.value) byKind.set(item.kind, [...(byKind.get(item.kind) ?? []), item]);
  return [...byKind.entries()].sort(([a], [b]) => a.localeCompare(b));
});
const canSave = computed(
  () => !props.disabled && !saving.value && !!kind.value && !!canonicalLabel.value.trim(),
);
const recorded = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(i18n.locale || undefined, { dateStyle: "medium", timeZone: i18n.timeZone });
};

async function load() {
  // After the first load the list refreshes in place, so the form (and keyboard focus)
  // is never torn down by a save or retire.
  loading.value = !loaded.value;
  loadError.value = "";
  try {
    const response = await corpusBuildsApi.semanticAliases(props.buildId);
    items.value = response.items;
    kinds.value = response.kinds;
    if (!kind.value && response.kinds.length) kind.value = response.kinds[0].kind;
    loaded.value = true;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (props.embedded) void load();
});

function resetForm() {
  editing.value = null;
  canonicalLabel.value = "";
  aliasText.value = "";
  reason.value = "";
  saveError.value = "";
}

function startEdit(item: SemanticAliasSet) {
  editing.value = item;
  kind.value = item.kind;
  canonicalLabel.value = item.canonical_label;
  aliasText.value = item.aliases.join("\n");
  reason.value = item.reason ?? "";
  saveError.value = "";
  status.value = "";
}

async function save() {
  if (!canSave.value) return;
  saving.value = true;
  saveError.value = "";
  try {
    const saved = await corpusBuildsApi.saveSemanticAlias(props.buildId, {
      kind: kind.value,
      canonical_label: canonicalLabel.value.trim(),
      aliases: aliasText.value
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
      reason: reason.value.trim(),
      replaces: editing.value?.alias_set_id ?? null,
    });
    status.value = tf("saved", { label: saved.canonical_label });
    resetForm();
    await load();
    emit("changed");
  } catch (error) {
    // A conflict names the surfaces that already belong to another identity.
    saveError.value = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}

async function openImport() {
  importing.value = true;
  importError.value = "";
  importSkipped.value = [];
  if (sources.value) return;
  importBusy.value = true;
  try {
    sources.value = (await corpusBuildsApi.semanticAliasSources(props.buildId)).items;
    if (sources.value.length) await chooseSource(sources.value[0].build_id);
  } catch (error) {
    importError.value = error instanceof Error ? error.message : String(error);
  } finally {
    importBusy.value = false;
  }
}

async function chooseSource(buildId: string) {
  sourceBuildId.value = buildId;
  sourceItems.value = [];
  selectedImports.value = [];
  importBusy.value = true;
  importError.value = "";
  try {
    sourceItems.value = (await corpusBuildsApi.semanticAliases(buildId)).items;
    selectedImports.value = sourceItems.value.map((item) => item.alias_set_id);
  } catch (error) {
    importError.value = error instanceof Error ? error.message : String(error);
  } finally {
    importBusy.value = false;
  }
}

async function runImport() {
  if (!sourceBuildId.value || !selectedImports.value.length) return;
  importBusy.value = true;
  importError.value = "";
  try {
    const result = await corpusBuildsApi.importSemanticAliases(
      props.buildId,
      sourceBuildId.value,
      selectedImports.value,
    );
    importSkipped.value = result.skipped.map((item) =>
      tf(
        item.reason === "already_imported" ? "import_skipped_already" : "import_skipped_conflict",
        {
          label: item.canonical_label,
        },
      ),
    );
    status.value = tf("import_done", {
      imported: result.imported.length,
      skipped: result.skipped.length,
    });
    await load();
    if (result.imported.length) emit("changed");
  } catch (error) {
    importError.value = error instanceof Error ? error.message : String(error);
  } finally {
    importBusy.value = false;
  }
}

async function retire(item: SemanticAliasSet) {
  saving.value = true;
  saveError.value = "";
  try {
    await corpusBuildsApi.retireSemanticAlias(props.buildId, item.alias_set_id);
    confirmingRetire.value = "";
    if (editing.value?.alias_set_id === item.alias_set_id) resetForm();
    status.value = tf("retired", { label: item.canonical_label });
    await load();
    emit("changed");
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <details
    class="alias-panel"
    :class="{ embedded: props.embedded }"
    :open="props.embedded || undefined"
    @toggle="(e) => (e.target as HTMLDetailsElement).open && !loaded && !loading && load()"
  >
    <summary v-if="!props.embedded">{{ t("title", "Reviewed identities") }}</summary>
    <p class="intro">{{ t("intro") }}</p>
    <UiLoadingState
      v-if="loading"
      variant="skeleton"
      :skeleton-count="3"
      :label="t('loading', 'Loading reviewed identities…')"
    />
    <p v-else-if="loadError" role="alert" class="error">
      {{ tf("load_failed", { error: loadError }) }}
      <UiButton size="small" :label="t('retry', 'Try again')" @click="load" />
    </p>
    <template v-else-if="loaded">
      <p class="status" role="status" aria-live="polite">{{ status }}</p>
      <p v-if="!items.length" class="empty">{{ t("empty", "No reviewed identities yet.") }}</p>
      <section v-for="[groupKind, sets] in grouped" :key="groupKind" class="kind-group">
        <h4>{{ groupKind }}</h4>
        <ul>
          <li v-for="item in sets" :key="item.alias_set_id" class="alias-set">
            <div class="alias-copy">
              <strong>{{ item.canonical_label }}</strong>
              <span class="forms">{{
                item.aliases.length ? item.aliases.join(" · ") : t("no_other_forms")
              }}</span>
              <small>
                {{ tf("recorded", { date: recorded(item.created_at) })
                }}<template v-if="item.reason"> — {{ item.reason }}</template>
              </small>
              <small v-if="item.imported_from">{{
                tf("imported_from", {
                  title: item.imported_from.build_title || item.imported_from.build_id,
                })
              }}</small>
            </div>
            <div class="alias-actions">
              <template v-if="confirmingRetire === item.alias_set_id">
                <span role="alert" class="confirm">{{
                  tf("retire_confirm", { label: item.canonical_label })
                }}</span>
                <UiButton
                  size="small"
                  variant="danger"
                  :label="t('confirm_retire', 'Retire')"
                  :disabled="disabled || saving"
                  @click="retire(item)"
                />
                <UiButton
                  size="small"
                  :label="t('cancel', 'Cancel')"
                  @click="confirmingRetire = ''"
                />
              </template>
              <template v-else>
                <UiButton
                  size="small"
                  :label="tf('edit', { label: item.canonical_label })"
                  :disabled="disabled || saving"
                  @click="startEdit(item)"
                />
                <UiButton
                  size="small"
                  variant="ghost"
                  :label="tf('retire', { label: item.canonical_label })"
                  :disabled="disabled || saving"
                  @click="confirmingRetire = item.alias_set_id"
                />
              </template>
            </div>
          </li>
        </ul>
      </section>

      <section class="alias-import" :aria-labelledby="`${formId}-import`">
        <h4 :id="`${formId}-import`">{{ t("import_title", "Import from another corpus") }}</h4>
        <p class="hint">{{ t("import_intro") }}</p>
        <UiButton
          v-if="!importing"
          size="small"
          :label="t('import_open', 'Import from another corpus…')"
          :disabled="disabled"
          @click="openImport"
        />
        <template v-else>
          <p v-if="importBusy && !sources" role="status">
            {{ t("import_loading", "Looking for other corpora…") }}
          </p>
          <p v-else-if="sources && !sources.length" class="empty">{{ t("import_none") }}</p>
          <template v-else-if="sources">
            <label :for="sourceId" class="import-source">
              <span>{{ t("import_source", "Corpus build") }}</span>
              <select
                :id="sourceId"
                class="control"
                :value="sourceBuildId"
                :disabled="disabled || importBusy"
                @change="chooseSource(($event.target as HTMLSelectElement).value)"
              >
                <option v-for="source in sources" :key="source.build_id" :value="source.build_id">
                  {{
                    tf("import_source_option", { title: source.title, count: source.alias_sets })
                  }}
                </option>
              </select>
            </label>
            <fieldset v-if="sourceItems.length" class="import-choices">
              <legend>{{ t("import_choose", "Identities to import") }}</legend>
              <label v-for="item in sourceItems" :key="item.alias_set_id" class="check">
                <input
                  v-model="selectedImports"
                  type="checkbox"
                  :value="item.alias_set_id"
                  :disabled="disabled || importBusy"
                />
                <span
                  >{{ item.canonical_label }} <small>({{ item.kind }})</small
                  ><template v-if="item.aliases.length">
                    — {{ item.aliases.join(" · ") }}</template
                  ></span
                >
              </label>
            </fieldset>
          </template>
          <p v-if="importError" role="alert" class="error">{{ importError }}</p>
          <ul v-if="importSkipped.length" class="skipped">
            <li v-for="line in importSkipped" :key="line">{{ line }}</li>
          </ul>
          <div class="form-actions">
            <UiButton
              v-if="sources?.length"
              variant="primary"
              size="small"
              :label="tf('import_submit', { count: selectedImports.length })"
              :disabled="disabled || importBusy || !selectedImports.length"
              @click="runImport"
            />
            <UiButton size="small" :label="t('import_close', 'Close')" @click="importing = false" />
          </div>
        </template>
      </section>

      <p v-if="!kinds.length" class="empty">{{ t("no_kinds") }}</p>
      <form v-else class="alias-form" :aria-labelledby="`${formId}-title`" @submit.prevent="save">
        <h4 :id="`${formId}-title`">
          {{
            editing ? tf("edit", { label: editing.canonical_label }) : t("save", "Save identity")
          }}
        </h4>
        <p v-if="editing" class="hint">{{ tf("editing", { label: editing.canonical_label }) }}</p>
        <div class="form-grid">
          <label :for="kindId">
            <span>{{ t("kind", "Kind") }}</span>
            <select :id="kindId" v-model="kind" class="control" :disabled="disabled || !!editing">
              <option v-for="option in kinds" :key="option.kind" :value="option.kind">
                {{ tf("kind_option", { kind: option.kind, fields: option.fields.join(", ") }) }}
              </option>
            </select>
          </label>
          <label :for="labelId">
            <span>{{ t("canonical_label", "Preferred form") }}</span>
            <input
              :id="labelId"
              v-model="canonicalLabel"
              class="control"
              type="text"
              maxlength="200"
              required
              :disabled="disabled"
            />
          </label>
          <label :for="aliasesId" class="wide">
            <span>{{ t("aliases", "Other forms, one per line") }}</span>
            <textarea
              :id="aliasesId"
              v-model="aliasText"
              class="control"
              rows="3"
              :disabled="disabled"
            />
          </label>
          <label :for="reasonId" class="wide">
            <span>{{ t("reason", "Note (optional)") }}</span>
            <input
              :id="reasonId"
              v-model="reason"
              class="control"
              type="text"
              maxlength="1000"
              :disabled="disabled"
            />
          </label>
        </div>
        <p v-if="saveError" role="alert" class="error">{{ saveError }}</p>
        <p class="hint">{{ t("distinct_note") }}</p>
        <div class="form-actions">
          <UiButton
            type="submit"
            variant="primary"
            :label="editing ? t('save_changes', 'Save changes') : t('save', 'Save identity')"
            :disabled="!canSave"
          />
          <UiButton v-if="editing" :label="t('cancel', 'Cancel')" @click="resetForm" />
        </div>
      </form>
    </template>
  </details>
</template>

<style scoped>
.alias-panel {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  padding: 0.5rem 0.875rem;
}
.alias-panel.embedded {
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0;
}
.alias-panel summary {
  cursor: pointer;
  font-weight: 700;
  padding: 0.375rem 0;
}
.alias-panel summary:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.intro,
.hint,
.empty {
  margin: 0.25rem 0 0.5rem;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.status:empty {
  display: none;
}
.status,
.error,
.confirm {
  font-size: var(--fs-sm);
}
.error {
  color: var(--tone-danger-fg);
  font-weight: 600;
}
.kind-group h4,
.alias-form h4 {
  margin: 0.75rem 0 0.25rem;
  font-size: var(--fs-sm);
}
.kind-group ul {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.alias-set {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: flex-start;
  justify-content: space-between;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.alias-copy {
  display: grid;
  gap: 2px;
  min-inline-size: 0;
  font-size: var(--fs-sm);
}
.alias-copy .forms {
  overflow-wrap: anywhere;
}
.alias-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.alias-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  align-items: center;
}
.alias-form {
  display: grid;
  gap: 0.5rem;
  margin-block-start: 0.5rem;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.5rem 0.75rem;
}
.form-grid label {
  display: grid;
  gap: 4px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.form-grid .wide {
  grid-column: 1 / -1;
}
.form-grid :is(input, select, textarea) {
  inline-size: 100%;
  font-weight: 500;
}
.control {
  min-block-size: 40px;
}
.alias-import {
  display: grid;
  gap: 0.375rem;
  margin-block-start: 0.5rem;
  justify-items: start;
}
.import-source {
  display: grid;
  gap: 4px;
  min-inline-size: min(100%, 24rem);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.import-choices {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}
.import-choices legend {
  padding: 0 4px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.check {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  font-size: var(--fs-sm);
  overflow-wrap: anywhere;
}
.skipped {
  margin: 0;
  padding-inline-start: 1.25rem;
  font-size: var(--fs-sm);
}
.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>

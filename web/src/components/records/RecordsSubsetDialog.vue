<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, markRaw, ref, useId } from "vue";
import { useI18nStore } from "../../stores/i18n";
import { notify } from "../../composables/notifications";
import UiDialog from "../ui/UiDialog.vue";
import type { SubsetRule } from "../../domain/recordQuery";
import type { SubsetField, SubsetRequest, SubsetSource } from "../../domain/recordSubsets";
import SubsetCondition from "./SubsetCondition.vue";
import {
  describeExpression,
  fieldValueSuggestions,
  recordMatchesExpression,
  type SubsetExpressionItem,
  type SubsetJoin,
} from "../../domain/subsetExpression";
import {
  SUBSET_PROFILES_LIMIT,
  SubsetProfilesImportError,
  exportSubsetProfiles,
  loadSubsetProfiles,
  mergeSubsetProfiles,
  parseSubsetProfilesImport,
  saveSubsetProfiles,
  type SubsetProfile,
} from "../../domain/subsetProfiles";

/**
 * Create JSONL subset: choose a source, build a filter expression, and create a new local file
 * holding the matching Records. Saved filter profiles can be reused, exported and imported.
 * The parent performs the creation (`create`), so this component never touches workspace state.
 */
const props = defineProps<{
  sources: SubsetSource[];
  fields: SubsetField[];
  defaultName: string;
  recordsFor: (source: string) => Record<string, unknown>[];
}>();
const emit = defineEmits<{ create: [request: SubsetRequest] }>();

const i18n = useI18nStore();
const id = useId();
const isOpen = ref(false);
const busy = ref(false);

interface DraftRule extends SubsetRule {
  id: number;
  value: string;
}
type DraftItem =
  | { id: number; type: "rule"; join: SubsetJoin; rule: DraftRule }
  | { id: number; type: "group"; join: SubsetJoin; mode: SubsetJoin; rules: DraftRule[] };

let nextId = 1;
const source = ref("active");
const name = ref("");
const caseSensitive = ref(false);
const items = ref<DraftItem[]>([]);
const profiles = ref<SubsetProfile[]>([]);
const profileId = ref("");
const savingProfile = ref(false);
const profileName = ref("");
const importInput = ref<HTMLInputElement | null>(null);

const fieldKeys = computed(() => props.fields.map((field) => field.key));
const preferredField = (...keys: string[]) =>
  keys.find((key) => fieldKeys.value.includes(key)) || fieldKeys.value[0] || "";
const newRule = (rule: Partial<SubsetRule> = {}): DraftRule => ({
  id: nextId++,
  field: rule.field && fieldKeys.value.includes(rule.field) ? rule.field : preferredField("work"),
  operator: rule.operator || "equals",
  value: rule.value == null ? "" : String(rule.value),
});

// ── The expression ────────────────────────────────────────────────────────────────────────────
const expression = computed<SubsetExpressionItem[]>(() =>
  items.value.map((item, index) => {
    const join = index === 0 ? "AND" : item.join;
    const plain = ({ field, operator, value }: DraftRule) => ({ field, operator, value });
    return item.type === "rule"
      ? { type: "rule", join, rule: plain(item.rule) }
      : { type: "group", join, mode: item.mode, rules: item.rules.map(plain) };
  }),
);
// The source records are the workspace's own objects: never make them reactive.
const sourceRecords = computed(() => markRaw(props.recordsFor(source.value)));
const matchCount = computed(() =>
  expression.value.length
    ? sourceRecords.value.filter((record) =>
        recordMatchesExpression(record, expression.value, caseSensitive.value),
      ).length
    : 0,
);
const fieldLabel = (key: string) => props.fields.find((field) => field.key === key)?.label || key;
const operatorLabel = (operator: string) => i18n.t(`subset.operator.${operator}`, operator);
const expressionText = computed(() =>
  describeExpression(expression.value, { field: fieldLabel, operator: operatorLabel }),
);
const suggestionCache = new Map<string, string[]>();
function suggestions(field: string) {
  const key = `${source.value}\u0000${field}`;
  if (!suggestionCache.has(key))
    suggestionCache.set(key, fieldValueSuggestions(sourceRecords.value, field, i18n.locale));
  return suggestionCache.get(key) || [];
}
const createBlocker = computed(() => {
  if (!expression.value.length) return i18n.t("subset.need_condition");
  if (!matchCount.value) return i18n.t("subset.no_matches");
  return "";
});

function addRule() {
  items.value.push({ id: nextId++, type: "rule", join: "AND", rule: newRule() });
}
function addGroup() {
  items.value.push({
    id: nextId++,
    type: "group",
    join: "AND",
    mode: "OR",
    rules: [
      newRule({ field: preferredField("topics"), operator: "array_contains" }),
      newRule({ field: preferredField("concepts"), operator: "array_contains" }),
    ],
  });
}
function removeItem(itemId: number) {
  items.value = items.value.filter((item) => item.id !== itemId);
}
function removeGroupRule(group: DraftItem & { type: "group" }, ruleId: number) {
  group.rules = group.rules.filter((rule) => rule.id !== ruleId);
  if (!group.rules.length) removeItem(group.id);
}
function sourceLabel(item: SubsetSource) {
  const count = item.count.toLocaleString(i18n.locale);
  if (item.id === "active") return i18n.tf("subset.source_active", { name: item.name });
  if (item.id === "all") return i18n.tf("subset.source_all", { count });
  return i18n.tf("subset.source_file", { name: item.name, count });
}

// ── Saved filter profiles ─────────────────────────────────────────────────────────────────────
function applyProfile(profile: SubsetProfile) {
  items.value = profile.expression.map((item) =>
    item.type === "group"
      ? {
          id: nextId++,
          type: "group",
          join: item.join,
          mode: item.mode,
          rules: item.rules.map(newRule),
        }
      : { id: nextId++, type: "rule", join: item.join, rule: newRule(item.rule) },
  );
  caseSensitive.value = profile.caseSensitive;
}
function chooseProfile(value: string) {
  profileId.value = value;
  const profile = profiles.value.find((item) => item.id === value);
  if (profile) applyProfile(profile);
}
function startSavingProfile() {
  profileName.value = profiles.value.find((item) => item.id === profileId.value)?.name || "";
  savingProfile.value = true;
}
function saveProfile() {
  const trimmed = profileName.value.trim();
  if (!trimmed || !expression.value.length) return;
  const profile: SubsetProfile = {
    id: crypto.randomUUID(),
    name: trimmed,
    expression: expression.value,
    caseSensitive: caseSensitive.value,
    created_at: new Date().toISOString(),
  };
  // Saving under an existing name updates that profile rather than adding a duplicate.
  const result = mergeSubsetProfiles(profiles.value, [profile], () => profile.id);
  saveSubsetProfiles(result.profiles);
  profiles.value = result.profiles;
  profileId.value =
    result.profiles.find((item) => item.name.toLocaleLowerCase() === trimmed.toLocaleLowerCase())
      ?.id || "";
  savingProfile.value = false;
  notify(i18n.tf("subset.profile_saved", { name: trimmed }), "success");
}
function deleteProfile() {
  const profile = profiles.value.find((item) => item.id === profileId.value);
  if (!profile) return;
  profiles.value = profiles.value.filter((item) => item.id !== profile.id);
  saveSubsetProfiles(profiles.value);
  profileId.value = "";
  notify(i18n.tf("subset.profile_deleted", { name: profile.name }), "info");
}
function exportProfiles() {
  const count = profiles.value.length;
  if (!count) return;
  const blob = new Blob([`${JSON.stringify(exportSubsetProfiles(profiles.value), null, 2)}\n`], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `derridai-subset-profiles-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  notify(
    i18n.tf(
      count === 1 ? "subset.profiles_exported_one" : "subset.profiles_exported_other",
      count === 1 ? "Exported {count} filter profile" : "Exported {count} filter profiles",
      { count: count.toLocaleString(i18n.locale) },
    ),
    "success",
  );
}
const IMPORT_ERRORS: Record<SubsetProfilesImportError["code"], [string, string]> = {
  not_json: ["subset.import_not_json", "Could not import: the file is not valid JSON."],
  wrong_format: [
    "subset.import_wrong_format",
    "Could not import: the file is not a DerridAI filter profile export.",
  ],
  newer_version: [
    "subset.import_newer_version",
    "Could not import: the file was exported by a newer version of DerridAI.",
  ],
  no_profiles: [
    "subset.import_no_profiles",
    "Could not import: the file has no usable filter profiles.",
  ],
};
async function importProfiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  try {
    const { profiles: incoming, skipped } = parseSubsetProfilesImport(await file.text());
    const result = mergeSubsetProfiles(profiles.value, incoming, () => crypto.randomUUID());
    saveSubsetProfiles(result.profiles);
    profiles.value = result.profiles;
    const parts = [
      i18n.tf("subset.profiles_imported", {
        added: result.added.toLocaleString(i18n.locale),
        replaced: result.replaced.toLocaleString(i18n.locale),
      }),
    ];
    if (skipped)
      parts.push(
        i18n.tf("subset.profiles_import_skipped", {
          count: skipped.toLocaleString(i18n.locale),
        }),
      );
    if (result.dropped)
      parts.push(
        i18n.tf("subset.profiles_import_dropped", {
          count: result.dropped.toLocaleString(i18n.locale),
          limit: SUBSET_PROFILES_LIMIT,
        }),
      );
    notify(parts.join(" · "), skipped || result.dropped ? "warning" : "success");
  } catch (error) {
    const known = error instanceof SubsetProfilesImportError ? IMPORT_ERRORS[error.code] : null;
    notify(
      known
        ? i18n.t(known[0], known[1])
        : i18n.tf("subset.import_failed", {
            error: error instanceof Error ? error.message : String(error),
          }),
      "danger",
    );
  }
}

// ── Open, close, create ───────────────────────────────────────────────────────────────────────
function open() {
  source.value = "active";
  name.value = props.defaultName;
  caseSensitive.value = false;
  profiles.value = loadSubsetProfiles();
  profileId.value = "";
  savingProfile.value = false;
  suggestionCache.clear();
  items.value = [
    {
      id: nextId++,
      type: "rule",
      join: "AND",
      rule: newRule({
        field: preferredField("document_author"),
        operator: "equals",
        value: "Jacques Derrida",
      }),
    },
  ];
  isOpen.value = true;
}
function close() {
  isOpen.value = false;
}
function create(download: boolean) {
  if (createBlocker.value || busy.value) return;
  busy.value = true;
  emit("create", {
    name: name.value,
    source: source.value,
    expression: expression.value,
    caseSensitive: caseSensitive.value,
    download,
  });
}
/** The parent calls this when creation has finished, successfully or not. */
function finish(created: boolean) {
  busy.value = false;
  if (created) close();
}

defineExpose({ open, close, finish });
</script>

<template>
  <UiDialog
    :open="isOpen"
    size="xlarge"
    :title="i18n.t('runtime.help.create_jsonl_subset')"
    :description="i18n.t('subset.dialog_help')"
    :close-label="i18n.t('common.close')"
    @close="close"
  >
    <div class="subset">
      <section class="subset-card" :aria-labelledby="`${id}-output`">
        <h3 :id="`${id}-output`">{{ i18n.t("subset.source_output") }}</h3>
        <div class="subset-grid">
          <label class="subset-field">
            <span>{{ i18n.t("subset.source") }}</span>
            <select v-model="source" class="control" @change="suggestionCache.clear()">
              <option v-for="item in sources" :key="item.id" :value="item.id">
                {{ sourceLabel(item) }}
              </option>
            </select>
          </label>
          <label class="subset-field">
            <span>{{ i18n.t("subset.file_name") }}</span>
            <input v-model="name" class="control" autocomplete="off" />
          </label>
        </div>
        <div class="subset-check">
          <label>
            <input v-model="caseSensitive" type="checkbox" :aria-describedby="`${id}-case-help`" />
            <span>{{ i18n.t("runtime.case_sensitive") }}</span>
          </label>
          <p :id="`${id}-case-help`" class="subset-help">
            {{ i18n.t("subset.case_sensitive_help") }}
          </p>
        </div>
      </section>

      <section class="subset-card" :aria-labelledby="`${id}-profiles`">
        <h3 :id="`${id}-profiles`">
          {{ i18n.t("subset.saved_profiles") }}
        </h3>
        <p class="subset-help">
          {{ i18n.t("subset.profiles_help") }}
        </p>
        <div class="subset-row">
          <label class="subset-field subset-grow">
            <span class="sr-only">{{ i18n.t("subset.saved_profile") }}</span>
            <select
              class="control"
              :value="profileId"
              @change="chooseProfile(($event.target as HTMLSelectElement).value)"
            >
              <option value="">{{ i18n.t("subset.no_saved_profile") }}</option>
              <option v-for="profile in profiles" :key="profile.id" :value="profile.id">
                {{ profile.name }}
              </option>
            </select>
          </label>
          <button
            type="button"
            class="btn"
            :disabled="!expression.length"
            @click="startSavingProfile"
          >
            {{ i18n.t("subset.save_profile") }}
          </button>
          <button type="button" class="btn danger" :disabled="!profileId" @click="deleteProfile">
            {{ i18n.t("common.delete") }}
          </button>
          <button type="button" class="btn" :disabled="!profiles.length" @click="exportProfiles">
            {{ i18n.t("subset.export_profiles") }}
          </button>
          <button type="button" class="btn" @click="importInput?.click()">
            {{ i18n.t("subset.import_profiles") }}
          </button>
          <input
            ref="importInput"
            type="file"
            accept="application/json,.json"
            hidden
            @change="importProfiles"
          />
        </div>
        <form v-if="savingProfile" class="subset-row" @submit.prevent="saveProfile">
          <label class="subset-field subset-grow">
            <span>{{ i18n.t("subset.profile_name") }}</span>
            <input v-model="profileName" class="control" autocomplete="off" required />
          </label>
          <button type="submit" class="btn primary" :disabled="!profileName.trim()">
            {{ i18n.t("subset.save_profile_confirm") }}
          </button>
          <button type="button" class="btn" @click="savingProfile = false">
            {{ i18n.t("common.cancel") }}
          </button>
        </form>
      </section>

      <section class="subset-card" :aria-labelledby="`${id}-filter`">
        <h3 :id="`${id}-filter`">{{ i18n.t("subset.filter") }}</h3>
        <p class="subset-help">
          {{ i18n.t("subset.filter_help") }}
        </p>
        <ol class="subset-items">
          <li v-for="(item, index) in items" :key="item.id" class="subset-item">
            <select
              v-if="index > 0"
              v-model="item.join"
              class="control subset-join"
              :aria-label="
                i18n.tf('subset.join_label', {
                  n: index + 1,
                })
              "
            >
              <option value="AND">{{ i18n.t("subset.and") }}</option>
              <option value="OR">{{ i18n.t("subset.or") }}</option>
            </select>
            <span v-else class="subset-join subset-where">{{ i18n.t("subset.where") }}</span>

            <SubsetCondition
              v-if="item.type === 'rule'"
              v-model:field="item.rule.field"
              v-model:operator="item.rule.operator"
              v-model:value="item.rule.value"
              :fields="fields"
              :suggestions="suggestions(item.rule.field)"
              :position="i18n.tf('subset.item_position', { n: index + 1 })"
              @remove="removeItem(item.id)"
            />

            <fieldset v-else class="subset-group">
              <legend>
                {{ i18n.tf("subset.group_legend", { n: index + 1 }) }}
              </legend>
              <div class="subset-row">
                <label class="subset-field">
                  <span>{{ i18n.t("subset.group_mode") }}</span>
                  <select v-model="item.mode" class="control">
                    <option value="OR">
                      {{ i18n.t("subset.match_any") }}
                    </option>
                    <option value="AND">
                      {{ i18n.t("subset.match_all") }}
                    </option>
                  </select>
                </label>
                <button
                  type="button"
                  class="btn"
                  @click="
                    item.rules.push(
                      newRule({ field: preferredField('topics'), operator: 'contains' }),
                    )
                  "
                >
                  {{ i18n.t("subset.add_condition") }}
                </button>
                <button type="button" class="btn danger" @click="removeItem(item.id)">
                  {{ i18n.t("subset.remove_group") }}
                </button>
              </div>
              <ul class="subset-group-rules">
                <li v-for="(rule, ruleIndex) in item.rules" :key="rule.id">
                  <SubsetCondition
                    v-model:field="rule.field"
                    v-model:operator="rule.operator"
                    v-model:value="rule.value"
                    :fields="fields"
                    :suggestions="suggestions(rule.field)"
                    :position="
                      i18n.tf('subset.group_condition_position', {
                        m: ruleIndex + 1,
                        n: index + 1,
                      })
                    "
                    @remove="removeGroupRule(item, rule.id)"
                  />
                </li>
              </ul>
            </fieldset>
          </li>
        </ol>
        <div class="subset-row">
          <button type="button" class="btn" @click="addRule">
            {{ i18n.t("subset.add_condition") }}
          </button>
          <button type="button" class="btn" @click="addGroup">
            {{ i18n.t("subset.add_group") }}
          </button>
          <p class="subset-count" role="status" aria-live="polite">
            {{
              expression.length
                ? i18n.tf("subset.match_count", {
                    matched: matchCount.toLocaleString(i18n.locale),
                    total: sourceRecords.length.toLocaleString(i18n.locale),
                  })
                : i18n.t("subset.need_condition")
            }}
          </p>
        </div>
        <p v-if="expressionText" class="subset-expression">
          <strong>{{ i18n.t("subset.expression") }}</strong>
          <code>{{ expressionText }}</code>
        </p>
      </section>
    </div>

    <template #footer>
      <p v-if="createBlocker" :id="`${id}-blocker`" class="subset-help">{{ createBlocker }}</p>
      <span v-else></span>
      <div class="subset-actions">
        <button type="button" class="btn" @click="close">
          {{ i18n.t("common.cancel") }}
        </button>
        <button
          type="button"
          class="btn"
          :disabled="Boolean(createBlocker) || busy"
          :aria-describedby="createBlocker ? `${id}-blocker` : undefined"
          @click="create(true)"
        >
          {{ i18n.t("subset.create_download") }}
        </button>
        <button
          type="button"
          class="btn primary"
          :disabled="Boolean(createBlocker) || busy"
          :aria-describedby="createBlocker ? `${id}-blocker` : undefined"
          @click="create(false)"
        >
          {{ i18n.t("subset.create_file") }}
        </button>
      </div>
    </template>
  </UiDialog>
</template>

<style scoped>
.subset {
  display: grid;
  gap: var(--space-4);
}
.subset-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.subset-card h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-base);
  font-weight: var(--fw-bold);
}
.subset-help {
  margin: 0;
  max-width: var(--measure);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.subset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: var(--space-3);
}
.subset-field {
  display: grid;
  gap: 4px;
  min-width: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.subset-check {
  display: grid;
  gap: 4px;
}
.subset-check label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-height-small);
  font-size: var(--fs-base);
  font-weight: var(--fw-semibold);
}
.subset-row {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: var(--space-2);
}
.subset-grow {
  flex: 1 1 14rem;
}
.subset-items,
.subset-group-rules {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.subset-item {
  display: grid;
  grid-template-columns: 5.5rem minmax(0, 1fr);
  gap: var(--space-2);
  align-items: start;
}
.subset-join {
  font-weight: var(--fw-bold);
}
.subset-where {
  align-self: center;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  text-align: center;
}
.subset-group {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.subset-group legend {
  padding: 0 4px;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}
.subset-group-rules {
  padding-left: var(--space-3);
  border-left: 2px solid var(--border-strong);
}
.subset-count {
  margin: 0 0 0 auto;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  font-variant-numeric: tabular-nums;
}
.subset-expression {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  font-size: var(--fs-sm);
}
.subset-expression code {
  font-family: var(--font-mono);
  overflow-wrap: anywhere;
}
.subset-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
@media (max-width: 760px) {
  .subset-item {
    grid-template-columns: 1fr;
  }
  .subset-join {
    width: 6rem;
  }
}
</style>

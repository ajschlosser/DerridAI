<script setup lang="ts">
/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, onMounted, ref } from "vue";
import {
  systemApi,
  type RetentionMode,
  type RetentionOverview,
  type RetentionPolicy,
  type RetentionRule,
  type RetentionStore,
} from "../../api/system";
import { pipelinePurposeLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const overview = ref<RetentionOverview | null>(null);
const draft = ref<RetentionPolicy | null>(null);
const busy = ref<"" | "load" | "save" | "apply" | "reclaim">("load");
const message = ref("");
const messageTone = ref<"info" | "danger">("info");
const confirming = ref<"" | "apply" | "reclaim">("");

const saved = computed(() => overview.value?.policy || null);
const dirty = computed(
  () =>
    Boolean(draft.value && saved.value) &&
    JSON.stringify(draft.value) !== JSON.stringify(saved.value),
);
const stores = computed(() => overview.value?.stores || []);
const pending = computed(() => ({
  count: stores.value.reduce((sum, store) => sum + (store.remove_count || 0), 0),
  bytes: stores.value.reduce((sum, store) => sum + (store.remove_bytes || 0), 0),
}));

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function bytes(value: number | undefined) {
  const amount = value || 0;
  const units = ["gigabyte", "megabyte", "kilobyte"] as const;
  const scale = [1e9, 1e6, 1e3];
  const index = scale.findIndex((size) => amount >= size);
  const unit = index === -1 ? "byte" : units[index];
  return new Intl.NumberFormat(i18n.locale, {
    style: "unit",
    unit,
    maximumFractionDigits: index === -1 ? 0 : 2,
  }).format(index === -1 ? amount : amount / scale[index]);
}

function count(value: number | undefined) {
  return new Intl.NumberFormat(i18n.locale).format(value || 0);
}

function date(value: string | null | undefined) {
  if (!value) return t("settings.retention_unknown", "Unknown");
  return new Intl.DateTimeFormat(i18n.locale, { dateStyle: "medium" }).format(new Date(value));
}

function storeLabel(store: RetentionStore) {
  if (store.kind === "pipeline_traces") {
    const feature = store.feature || "";
    const purpose = feature.split(".")[0];
    const label = pipelinePurposeLabel(purpose, t);
    return i18n.tf("settings.retention_store_traces", {
      feature: label === purpose ? feature : label,
    });
  }
  const labels: Record<string, string> = {
    pipeline_benchmark_runs: t("settings.retention_store_benchmarks", "Pipeline benchmark results"),
    job_history: t("settings.retention_store_jobs", "Finished job history"),
    response_cache: t("settings.retention_store_responses", "Saved Research responses"),
  };
  return labels[store.kind] || store.store_id;
}

function ruleSummary(rule: RetentionRule) {
  if (rule.mode === "max_age_days")
    return i18n.tf("settings.retention_rule_days", { days: count(rule.value || 0) });
  if (rule.mode === "max_size_gb")
    return i18n.tf("settings.retention_rule_size", { size: String(rule.value) });
  return t("settings.retention_rule_keep", "keep everything");
}

function ruleError(rule: RetentionRule) {
  const value = Number(rule.value);
  if (rule.mode === "max_age_days" && !(Number.isInteger(value) && value >= 1 && value <= 36500))
    return t("settings.retention_invalid_days", "Enter whole days from 1 to 36500.");
  if (rule.mode === "max_size_gb" && !(value >= 0.001 && value <= 100000))
    return t("settings.retention_invalid_size", "Enter between 0.001 and 100000 GB.");
  return "";
}

const invalid = computed(() => {
  if (!draft.value) return true;
  return [draft.value.default, ...Object.values(draft.value.stores)].some((rule) =>
    ruleError(rule),
  );
});

function storeRule(storeId: string): RetentionRule {
  if (!draft.value) return { mode: "inherit", value: null };
  return draft.value.stores[storeId] || { mode: "inherit", value: null };
}

function setMode(rule: RetentionRule, mode: RetentionMode) {
  rule.mode = mode;
  if (mode === "max_age_days")
    rule.value = rule.value && Number.isInteger(rule.value) ? rule.value : 90;
  else if (mode === "max_size_gb") rule.value = rule.value || 1;
  else rule.value = null;
}

function setStoreMode(storeId: string, mode: RetentionMode) {
  if (!draft.value) return;
  const rule = { ...storeRule(storeId) };
  setMode(rule, mode);
  if (mode === "inherit") delete draft.value.stores[storeId];
  else draft.value.stores[storeId] = rule;
}

function setStoreValue(storeId: string, raw: string) {
  const rule = storeRule(storeId);
  if (draft.value && rule.mode !== "inherit")
    draft.value.stores[storeId] = { ...rule, value: raw === "" ? null : Number(raw) };
}

function fail(exc: unknown) {
  messageTone.value = "danger";
  message.value = i18n.tf("settings.retention_failed", {
    message: exc instanceof Error ? exc.message : String(exc),
  });
}

function say(text: string) {
  messageTone.value = "info";
  message.value = text;
}

async function load() {
  busy.value = "load";
  try {
    overview.value = await systemApi.dataRetention();
    draft.value = clone(overview.value.policy);
  } catch (exc) {
    fail(exc);
  } finally {
    busy.value = "";
  }
}

async function save() {
  if (!draft.value || invalid.value) return;
  busy.value = "save";
  try {
    overview.value = await systemApi.setDataRetention(draft.value);
    draft.value = clone(overview.value.policy);
    say(
      t(
        "settings.retention_saved",
        "Retention policy saved. Nothing is removed until it is applied.",
      ),
    );
  } catch (exc) {
    fail(exc);
  } finally {
    busy.value = "";
  }
}

async function previewApply() {
  busy.value = "load";
  try {
    overview.value = await systemApi.dataRetention();
  } catch (exc) {
    fail(exc);
    return;
  } finally {
    busy.value = "";
  }
  if (!pending.value.count) {
    say(t("settings.retention_nothing_to_apply", "The saved policy removes nothing right now."));
    return;
  }
  confirming.value = "apply";
}

async function apply() {
  confirming.value = "";
  busy.value = "apply";
  try {
    const result = await systemApi.applyDataRetention();
    const removed = result.stores.reduce((sum, store) => sum + (store.removed_count || 0), 0);
    overview.value = await systemApi.dataRetention();
    say(i18n.tf("settings.retention_applied", { count: count(removed) }));
  } catch (exc) {
    fail(exc);
  } finally {
    busy.value = "";
  }
}

async function reclaim() {
  confirming.value = "";
  busy.value = "reclaim";
  try {
    const result = await systemApi.reclaimDataRetentionSpace();
    say(
      i18n.tf("settings.retention_reclaimed", {
        before: bytes(result.bytes_before),
        after: bytes(result.bytes_after),
      }),
    );
  } catch (exc) {
    fail(exc);
  } finally {
    busy.value = "";
  }
}

onMounted(load);
</script>

<template>
  <div class="retention" :aria-busy="busy !== ''">
    <p v-if="message" class="retention-message" :data-tone="messageTone" role="status">
      {{ message }}
    </p>
    <p v-if="busy === 'load' && !overview" role="status">{{ t("common.loading", "Loading") }}</p>

    <template v-if="draft && overview">
      <details class="retention-canonical">
        <summary>{{ t("settings.retention_canonical_title", "Kept permanently") }}</summary>
        <p>
          {{
            t(
              "settings.retention_canonical_help",
              "Corpus records and sources, review decisions and field assertions, metadata precedents, validated claims, response memory, pipeline definitions and benchmark cases, and user accounts are canonical and never expire.",
            )
          }}
        </p>
      </details>

      <fieldset class="retention-system">
        <legend>{{ t("settings.retention_system_legend", "System-wide policy") }}</legend>
        <p id="retention-system-help" class="retention-sub">
          {{
            t(
              "settings.retention_system_help",
              "Applies to every store that uses the system-wide policy. A size cap applies to each store separately.",
            )
          }}
        </p>
        <label class="retention-choice">
          <input
            type="radio"
            name="retention-system-mode"
            :checked="draft.default.mode === 'keep'"
            aria-describedby="retention-system-help"
            @change="setMode(draft.default, 'keep')"
          />
          {{ t("settings.retention_mode_keep", "Keep everything") }}
        </label>
        <div class="retention-choice">
          <label>
            <input
              type="radio"
              name="retention-system-mode"
              :checked="draft.default.mode === 'max_age_days'"
              @change="setMode(draft.default, 'max_age_days')"
            />
            {{ t("settings.retention_mode_days", "Remove records older than") }}
          </label>
          <input
            v-if="draft.default.mode === 'max_age_days'"
            v-model.number="draft.default.value"
            class="control retention-number"
            type="number"
            min="1"
            max="36500"
            step="1"
            :aria-label="t('settings.retention_days_label', 'Number of days')"
            :aria-invalid="Boolean(ruleError(draft.default))"
          />
          <span v-if="draft.default.mode === 'max_age_days'">{{
            t("settings.retention_days_unit", "days")
          }}</span>
        </div>
        <div class="retention-choice">
          <label>
            <input
              type="radio"
              name="retention-system-mode"
              :checked="draft.default.mode === 'max_size_gb'"
              @change="setMode(draft.default, 'max_size_gb')"
            />
            {{ t("settings.retention_mode_size", "Cap store size at") }}
          </label>
          <input
            v-if="draft.default.mode === 'max_size_gb'"
            v-model.number="draft.default.value"
            class="control retention-number"
            type="number"
            min="0.001"
            max="100000"
            step="0.1"
            :aria-label="t('settings.retention_gb_label', 'Size in gigabytes')"
            :aria-invalid="Boolean(ruleError(draft.default))"
          />
          <span v-if="draft.default.mode === 'max_size_gb'">{{
            t("settings.retention_gb_unit", "GB")
          }}</span>
        </div>
        <p v-if="ruleError(draft.default)" class="retention-error" role="alert">
          {{ ruleError(draft.default) }}
        </p>
      </fieldset>

      <table class="retention-table">
        <caption class="sr-only">
          {{
            t("settings.retention_stores_caption", "Operational data stores")
          }}
        </caption>
        <thead>
          <tr>
            <th scope="col">{{ t("settings.retention_col_store", "Store") }}</th>
            <th scope="col">{{ t("settings.retention_col_size", "Records and size") }}</th>
            <th scope="col">{{ t("settings.retention_col_oldest", "Oldest record") }}</th>
            <th scope="col">{{ t("settings.retention_col_rule", "Rule") }}</th>
            <th scope="col">
              {{ t("settings.retention_col_remove", "Removed by the saved policy now") }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="store in stores" :key="store.store_id">
            <th scope="row">
              {{ storeLabel(store) }}
              <span v-if="store.error" class="retention-error">{{
                i18n.tf("settings.retention_store_error", { message: store.error })
              }}</span>
            </th>
            <td>
              {{
                i18n.tf("settings.retention_records", {
                  count: count(store.count),
                  size: bytes(store.bytes),
                })
              }}
              <span v-if="store.pinned_count" class="retention-sub">{{
                i18n.tf("settings.retention_pinned", { count: count(store.pinned_count) })
              }}</span>
            </td>
            <td>{{ date(store.oldest_at) }}</td>
            <td>
              <div class="retention-rule">
                <select
                  class="control"
                  :value="storeRule(store.store_id).mode"
                  :aria-label="i18n.tf('settings.retention_rule_for', { store: storeLabel(store) })"
                  @change="
                    setStoreMode(
                      store.store_id,
                      ($event.target as HTMLSelectElement).value as RetentionMode,
                    )
                  "
                >
                  <option value="inherit">
                    {{ t("settings.retention_mode_inherit", "Use system-wide policy") }}
                  </option>
                  <option value="keep">
                    {{ t("settings.retention_mode_keep", "Keep everything") }}
                  </option>
                  <option value="max_age_days">
                    {{ t("settings.retention_mode_days", "Remove records older than") }}
                  </option>
                  <option value="max_size_gb">
                    {{ t("settings.retention_mode_size", "Cap store size at") }}
                  </option>
                </select>
                <template
                  v-if="['max_age_days', 'max_size_gb'].includes(storeRule(store.store_id).mode)"
                >
                  <input
                    class="control retention-number"
                    type="number"
                    :min="storeRule(store.store_id).mode === 'max_age_days' ? 1 : 0.001"
                    :step="storeRule(store.store_id).mode === 'max_age_days' ? 1 : 0.1"
                    :value="storeRule(store.store_id).value ?? ''"
                    :aria-label="
                      storeRule(store.store_id).mode === 'max_age_days'
                        ? t('settings.retention_days_label', 'Number of days')
                        : t('settings.retention_gb_label', 'Size in gigabytes')
                    "
                    :aria-invalid="Boolean(ruleError(storeRule(store.store_id)))"
                    @input="
                      setStoreValue(store.store_id, ($event.target as HTMLInputElement).value)
                    "
                  />
                  <span>{{
                    storeRule(store.store_id).mode === "max_age_days"
                      ? t("settings.retention_days_unit", "days")
                      : t("settings.retention_gb_unit", "GB")
                  }}</span>
                </template>
              </div>
              <span v-if="ruleError(storeRule(store.store_id))" class="retention-error">{{
                ruleError(storeRule(store.store_id))
              }}</span>
              <span v-else class="retention-sub">{{
                i18n.tf("settings.retention_effective", { rule: ruleSummary(store.effective_rule) })
              }}</span>
            </td>
            <td>
              {{
                store.remove_count
                  ? i18n.tf("settings.retention_records", {
                      count: count(store.remove_count),
                      size: bytes(store.remove_bytes),
                    })
                  : t("settings.retention_nothing", "Nothing")
              }}
              <span v-if="store.warnings?.includes('pinned_exceeds_cap')" class="retention-sub">{{
                t(
                  "settings.retention_pinned_over_cap",
                  "Records that must be kept already exceed this cap.",
                )
              }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <p class="retention-sub">
        {{
          t(
            "settings.retention_schedule_note",
            "A saved policy is also applied automatically every hour.",
          )
        }}
      </p>
      <div class="retention-actions">
        <UiButton
          variant="primary"
          :label="t('settings.retention_save', 'Save retention policy')"
          :disabled="!dirty || invalid || busy !== ''"
          @click="save"
        />
        <UiButton
          variant="danger"
          :label="t('settings.retention_apply', 'Apply now…')"
          :disabled="dirty || busy !== ''"
          :disabled-reason="
            dirty
              ? t('settings.retention_unsaved', 'Save the policy before applying it.')
              : undefined
          "
          @click="previewApply"
        />
        <UiButton
          :label="t('settings.retention_reclaim', 'Reclaim disk space…')"
          :disabled="busy !== ''"
          @click="confirming = 'reclaim'"
        />
      </div>
    </template>

    <UiDialog
      :open="confirming === 'apply'"
      :title="t('settings.retention_apply_title', 'Remove operational data now?')"
      @close="confirming = ''"
    >
      <p>
        {{
          i18n.tf("settings.retention_apply_body", {
            count: count(pending.count),
            size: bytes(pending.bytes),
          })
        }}
      </p>
      <template #footer>
        <UiButton :label="t('common.cancel', 'Cancel')" @click="confirming = ''" />
        <UiButton
          variant="danger"
          :label="i18n.tf('settings.retention_apply_confirm', { count: count(pending.count) })"
          @click="apply"
        />
      </template>
    </UiDialog>
    <UiDialog
      :open="confirming === 'reclaim'"
      :title="t('settings.retention_reclaim_title', 'Reclaim disk space?')"
      @close="confirming = ''"
    >
      <p>
        {{
          t(
            "settings.retention_reclaim_body",
            "Compacting the system database returns space from removed records to the disk. Other work may pause briefly while it runs.",
          )
        }}
      </p>
      <template #footer>
        <UiButton :label="t('common.cancel', 'Cancel')" @click="confirming = ''" />
        <UiButton
          variant="primary"
          :label="t('settings.retention_reclaim_confirm', 'Compact database')"
          @click="reclaim"
        />
      </template>
    </UiDialog>
  </div>
</template>

<style scoped>
.retention {
  display: grid;
  gap: 12px;
}
.retention-system {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}
.retention-system legend {
  font-weight: 700;
}
.retention-choice,
.retention-rule {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.retention-number {
  width: 7rem;
}
.retention-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}
.retention-table :is(th, td) {
  padding: 8px;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--border-subtle);
}
.retention-sub {
  display: block;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.retention-error,
.retention-message[data-tone="danger"] {
  display: block;
  color: var(--tone-danger-fg);
}
.retention-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
@media (max-width: 720px) {
  .retention-table thead {
    display: none;
  }
  .retention-table :is(tr, th, td) {
    display: block;
  }
}
</style>

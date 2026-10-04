<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed } from "vue";
import {
  clearStageOverride,
  effectiveOverrideValue,
  hasStageOverride,
  setStageOverride,
  stageOverrideValue,
} from "../../domain/pipelineOverrides";
import {
  pipelineConfigHelp,
  pipelineConfigLabel,
  pipelineConfigOptionLabel,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineConfigOverrideSet,
  PipelineDefinition,
  PipelineStage,
  PipelineStrategy,
} from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = withDefaults(
  defineProps<{
    pipeline: PipelineDefinition | null;
    strategies: PipelineStrategy[];
    modelValue: PipelineConfigOverrideSet | null;
    /** Settings-level overrides inherited by a run-specific editor. */
    inheritedOverrides?: PipelineConfigOverrideSet | null;
    layer: "settings" | "run";
    disabled?: boolean;
  }>(),
  {
    inheritedOverrides: null,
    disabled: false,
  },
);
const emit = defineEmits<{
  "update:modelValue": [value: PipelineConfigOverrideSet | null];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

type ConfigRow = {
  stage: PipelineStage;
  strategy: PipelineStrategy;
  key: string;
  rule: Record<string, unknown>;
};

const rowsByStage = computed(() => {
  if (!props.pipeline)
    return [] as Array<{ stage: PipelineStage; strategy: PipelineStrategy; rows: ConfigRow[] }>;
  const strategies = new Map(props.strategies.map((item) => [item.strategy_id, item]));
  return props.pipeline.stages
    .map((stage) => {
      const strategy = strategies.get(stage.strategy);
      const schema = strategy?.config_schema;
      const properties =
        schema && typeof schema === "object" && !Array.isArray(schema)
          ? (schema as { properties?: unknown }).properties
          : null;
      const entries =
        properties && typeof properties === "object" && !Array.isArray(properties)
          ? Object.entries(properties as Record<string, Record<string, unknown>>)
          : [];
      if (
        Object.prototype.hasOwnProperty.call(stage.config || {}, "optional") &&
        !entries.some(([key]) => key === "optional")
      ) {
        entries.push(["optional", { type: "boolean" }]);
      }
      return {
        stage,
        strategy,
        rows: strategy ? entries.map(([key, rule]) => ({ stage, strategy, key, rule })) : [],
      };
    })
    .filter(
      (item): item is { stage: PipelineStage; strategy: PipelineStrategy; rows: ConfigRow[] } =>
        Boolean(item.strategy && item.rows.length),
    );
});

function enumValues(rule: Record<string, unknown>): string[] | null {
  return Array.isArray(rule.enum) ? rule.enum.map(String) : null;
}

function seedValue(row: ConfigRow): unknown {
  const effective = effectiveOverrideValue({
    stage: row.stage,
    key: row.key,
    rule: row.rule,
    settingsOverrides: props.inheritedOverrides,
    runOverrides: props.modelValue,
  }).value;
  if (effective !== undefined) return effective;
  if (Object.prototype.hasOwnProperty.call(row.rule, "default")) return row.rule.default;
  if (row.rule.type === "boolean") return false;
  const values = enumValues(row.rule);
  if (values?.length) return values[0];
  if (row.rule.type === "integer" || row.rule.type === "number") {
    return typeof row.rule.minimum === "number" ? row.rule.minimum : 0;
  }
  return "";
}

function toggleOverride(row: ConfigRow, enabled: boolean) {
  if (!props.pipeline) return;
  const next = enabled
    ? setStageOverride(props.pipeline, props.modelValue, row.stage.id, row.key, seedValue(row))
    : clearStageOverride(props.pipeline, props.modelValue, row.stage.id, row.key);
  emit("update:modelValue", next);
}

function updateValue(row: ConfigRow, raw: string | boolean) {
  if (!props.pipeline) return;
  let value: unknown = raw;
  if (row.rule.type === "integer") value = Number.parseInt(String(raw), 10);
  else if (row.rule.type === "number") value = Number(raw);
  else if (row.rule.type === "boolean") value = Boolean(raw);
  emit(
    "update:modelValue",
    setStageOverride(props.pipeline, props.modelValue, row.stage.id, row.key, value),
  );
}

function displayValue(value: unknown): string {
  if (value === undefined) return t("pipelines.override_not_set", "Not set");
  if (value === null) return "—";
  if (typeof value === "boolean") return value ? t("common.yes", "Yes") : t("common.no", "No");
  return String(value);
}

function resolved(row: ConfigRow) {
  return effectiveOverrideValue({
    stage: row.stage,
    key: row.key,
    rule: row.rule,
    settingsOverrides: props.inheritedOverrides,
    runOverrides: props.modelValue,
  });
}

function localValue(row: ConfigRow) {
  const value = stageOverrideValue(props.modelValue, row.stage.id, row.key);
  return value === undefined ? seedValue(row) : value;
}

function sourceLabel(source: "pipeline" | "settings" | "run") {
  if (source === "run") return t("pipelines.override_source_run", "This run");
  if (source === "settings") return t("pipelines.override_source_settings", "Settings");
  return t("pipelines.override_source_pipeline", "Pipeline Studio");
}
</script>

<template>
  <div class="pipeline-override-editor">
    <div v-if="!pipeline" class="pipeline-override-empty" role="status">
      {{
        t(
          "pipelines.override_select_pipeline",
          "Select a Research pipeline to configure overrides.",
        )
      }}
    </div>
    <div v-else-if="!rowsByStage.length" class="pipeline-override-empty" role="status">
      {{
        t(
          "pipelines.override_no_config",
          "This pipeline has no registered stage configuration that can be overridden.",
        )
      }}
    </div>

    <template v-else>
      <fieldset v-for="group in rowsByStage" :key="group.stage.id" class="pipeline-override-stage">
        <legend>
          <span>{{ group.stage.id }}</span>
          <small>{{ pipelineStrategyLabel(group.strategy, t) }}</small>
        </legend>

        <div class="pipeline-override-rows">
          <div
            v-for="row in group.rows"
            :key="row.key"
            class="pipeline-override-row"
            :data-overridden="hasStageOverride(modelValue, row.stage.id, row.key)"
          >
            <div class="pipeline-override-heading">
              <label :for="`override-${layer}-${row.stage.id}-${row.key}`">
                <input
                  :id="`override-${layer}-${row.stage.id}-${row.key}`"
                  type="checkbox"
                  :checked="hasStageOverride(modelValue, row.stage.id, row.key)"
                  :disabled="disabled"
                  @change="toggleOverride(row, ($event.target as HTMLInputElement).checked)"
                />
                <span>
                  {{ pipelineConfigLabel(row.key, t) }}
                  <code>{{ row.stage.id }}.{{ row.key }}</code>
                </span>
              </label>
              <UiTooltip
                :text="pipelineConfigHelp(row.key, t)"
                :label="t('pipelines.explain_setting', 'Explain this setting')"
              />
            </div>

            <div
              v-if="hasStageOverride(modelValue, row.stage.id, row.key)"
              class="pipeline-override-control"
            >
              <input
                v-if="row.rule.type === 'number' || row.rule.type === 'integer'"
                class="control"
                type="number"
                :step="row.rule.type === 'integer' ? 1 : 'any'"
                :min="typeof row.rule.minimum === 'number' ? row.rule.minimum : undefined"
                :max="typeof row.rule.maximum === 'number' ? row.rule.maximum : undefined"
                :value="localValue(row)"
                :disabled="disabled"
                @input="updateValue(row, ($event.target as HTMLInputElement).value)"
              />
              <select
                v-else-if="row.rule.type === 'boolean'"
                class="control"
                :value="String(localValue(row))"
                :disabled="disabled"
                @change="updateValue(row, ($event.target as HTMLSelectElement).value === 'true')"
              >
                <option value="true">{{ t("common.yes", "Yes") }}</option>
                <option value="false">{{ t("common.no", "No") }}</option>
              </select>
              <select
                v-else-if="enumValues(row.rule)"
                class="control"
                :value="String(localValue(row))"
                :disabled="disabled"
                @change="updateValue(row, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="option in enumValues(row.rule)" :key="option" :value="option">
                  {{ pipelineConfigOptionLabel(row.key, option, t) }}
                </option>
              </select>
              <input
                v-else
                class="control"
                :value="String(localValue(row))"
                :disabled="disabled"
                @input="updateValue(row, ($event.target as HTMLInputElement).value)"
              />
            </div>

            <dl class="pipeline-override-provenance">
              <div>
                <dt>{{ t("pipelines.override_pipeline_value", "Pipeline") }}</dt>
                <dd>{{ displayValue(resolved(row).pipeline) }}</dd>
              </div>
              <div v-if="layer === 'run'">
                <dt>{{ t("pipelines.override_settings_value", "Settings") }}</dt>
                <dd>{{ displayValue(resolved(row).settings) }}</dd>
              </div>
              <div>
                <dt>{{ t("pipelines.override_effective_value", "Effective") }}</dt>
                <dd>
                  <strong>{{ displayValue(resolved(row).value) }}</strong>
                  <small>{{ sourceLabel(resolved(row).source) }}</small>
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </fieldset>
    </template>
  </div>
</template>

<style scoped>
.pipeline-override-editor {
  display: grid;
  gap: var(--space-4);
}
.pipeline-override-empty {
  padding: var(--space-3);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-control);
  color: var(--text-secondary);
}
.pipeline-override-stage {
  min-width: 0;
  margin: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
}
.pipeline-override-stage legend {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
  padding-inline: var(--space-1);
  font-weight: var(--fw-bold);
}
.pipeline-override-stage legend small {
  color: var(--text-tertiary);
  font-weight: var(--fw-regular);
}
.pipeline-override-rows {
  display: grid;
  gap: var(--space-2);
}
.pipeline-override-row {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.pipeline-override-row[data-overridden="true"] {
  box-shadow: inset 3px 0 0 var(--accent);
}
.pipeline-override-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
}
.pipeline-override-heading label {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
  cursor: pointer;
}
.pipeline-override-heading label > span {
  display: grid;
  gap: 2px;
  min-width: 0;
  font-weight: var(--fw-bold);
}
.pipeline-override-heading code {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: var(--fw-regular);
  overflow-wrap: anywhere;
}
.pipeline-override-control {
  max-width: 24rem;
}
.pipeline-override-control .control {
  width: 100%;
}
.pipeline-override-provenance {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  margin: 0;
}
.pipeline-override-provenance div {
  display: grid;
  gap: 1px;
}
.pipeline-override-provenance dt {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.pipeline-override-provenance dd {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.pipeline-override-provenance small {
  color: var(--text-tertiary);
}
@media (max-width: 640px) {
  .pipeline-override-provenance {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>

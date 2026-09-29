<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelineStage,
  PipelineStrategy,
} from "../../types/pipelines";

const props = defineProps<{
  modelValue: PipelineDefinition;
  strategies: PipelineStrategy[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: PipelineDefinition];
}>();

const i18n = useI18nStore();
const strategyMap = computed(
  () => new Map(props.strategies.map((strategy) => [strategy.strategy_id, strategy])),
);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function clonePipeline(): PipelineDefinition {
  return structuredClone(props.modelValue);
}
function updateRoot<K extends keyof PipelineDefinition>(key: K, value: PipelineDefinition[K]) {
  const next = clonePipeline();
  next[key] = value;
  emit("update:modelValue", next);
}
function configProperties(stage: PipelineStage) {
  const schema = strategyMap.value.get(stage.strategy)?.config_schema;
  if (!schema || typeof schema !== "object") return [] as Array<[string, Record<string, unknown>]>;
  const properties = (schema as { properties?: unknown }).properties;
  if (!properties || typeof properties !== "object" || Array.isArray(properties)) return [];
  return Object.entries(properties as Record<string, Record<string, unknown>>);
}
function configValue(stage: PipelineStage, key: string, rule: Record<string, unknown>) {
  if (stage.config[key] !== undefined) return stage.config[key];
  if (rule.default !== undefined) return rule.default;
  return "";
}
function updateConfig(
  stageIndex: number,
  key: string,
  raw: string | boolean,
  rule: Record<string, unknown>,
) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  const kind = String(rule.type || "string");
  if (kind === "boolean") {
    stage.config[key] = Boolean(raw);
  } else if (kind === "integer" || kind === "number") {
    const value = Number(raw);
    if (raw === "" || !Number.isFinite(value)) delete stage.config[key];
    else stage.config[key] = kind === "integer" ? Math.trunc(value) : value;
  } else if (String(raw).trim() === "") {
    delete stage.config[key];
  } else {
    stage.config[key] = String(raw);
  }
  emit("update:modelValue", next);
}
</script>

<template>
  <div class="pipeline-editor">
    <div class="identity-grid">
      <label>
        <span>{{ t("pipelines.pipeline_id", "Pipeline ID") }}</span>
        <input
          class="control"
          :value="modelValue.pipeline_id"
          autocomplete="off"
          @input="updateRoot('pipeline_id', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label>
        <span>{{ t("pipelines.version", "Version") }}</span>
        <input
          class="control"
          type="number"
          min="1"
          step="1"
          :value="modelValue.version"
          @input="
            updateRoot(
              'version',
              Math.max(1, Number(($event.target as HTMLInputElement).value) || 1),
            )
          "
        />
      </label>
      <label class="identity-name">
        <span>{{ t("pipelines.name", "Name") }}</span>
        <input
          class="control"
          :value="modelValue.name"
          @input="updateRoot('name', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label>
        <span>{{ t("pipelines.status", "Status") }}</span>
        <select
          class="control"
          :value="modelValue.status"
          @change="
            updateRoot(
              'status',
              ($event.target as HTMLSelectElement).value as PipelineDefinition['status'],
            )
          "
        >
          <option value="draft">{{ t("pipelines.status_draft", "Draft") }}</option>
          <option value="active">{{ t("pipelines.status_active", "Active") }}</option>
          <option value="disabled">{{ t("pipelines.status_disabled", "Disabled") }}</option>
        </select>
      </label>
    </div>

    <label class="notes-field">
      <span>{{ t("pipelines.notes", "Notes") }}</span>
      <textarea
        class="control"
        rows="3"
        :value="modelValue.notes || ''"
        @input="updateRoot('notes', ($event.target as HTMLTextAreaElement).value || null)"
      />
    </label>

    <section class="stage-settings" :aria-label="t('pipelines.stage_settings', 'Stage settings')">
      <header>
        <div>
          <h4>{{ t("pipelines.stage_settings", "Stage settings") }}</h4>
          <p>
            {{
              t(
                "pipelines.stage_settings_help",
                "Only parameters declared by the registered server strategy are editable here.",
              )
            }}
          </p>
        </div>
      </header>

      <article
        v-for="(stage, stageIndex) in modelValue.stages"
        :key="stage.id"
        class="stage-settings-card"
      >
        <div class="stage-settings-heading">
          <div>
            <strong>{{ strategyMap.get(stage.strategy)?.label || stage.strategy }}</strong>
            <code>{{ stage.id }}</code>
          </div>
          <span>{{ strategyMap.get(stage.strategy)?.family || "unknown" }}</span>
        </div>

        <div v-if="configProperties(stage).length" class="config-grid">
          <label v-for="[key, rule] in configProperties(stage)" :key="key">
            <span>{{ key }}</span>
            <input
              v-if="rule.type === 'number' || rule.type === 'integer'"
              class="control"
              type="number"
              :step="rule.type === 'integer' ? 1 : 'any'"
              :min="typeof rule.minimum === 'number' ? rule.minimum : undefined"
              :max="typeof rule.maximum === 'number' ? rule.maximum : undefined"
              :value="configValue(stage, key, rule) as string | number"
              @input="
                updateConfig(
                  stageIndex,
                  key,
                  ($event.target as HTMLInputElement).value,
                  rule,
                )
              "
            />
            <select
              v-else-if="rule.type === 'boolean'"
              class="control"
              :value="String(configValue(stage, key, rule))"
              @change="
                updateConfig(
                  stageIndex,
                  key,
                  ($event.target as HTMLSelectElement).value === 'true',
                  rule,
                )
              "
            >
              <option value="true">{{ t("common.yes", "Yes") }}</option>
              <option value="false">{{ t("common.no", "No") }}</option>
            </select>
            <input
              v-else
              class="control"
              :value="String(configValue(stage, key, rule))"
              @input="
                updateConfig(
                  stageIndex,
                  key,
                  ($event.target as HTMLInputElement).value,
                  rule,
                )
              "
            />
          </label>
        </div>
        <p v-else class="no-config">
          {{ t("pipelines.no_stage_settings", "This stage has no configurable parameters.") }}
        </p>
      </article>
    </section>
  </div>
</template>

<style scoped>
.pipeline-editor {
  display: grid;
  gap: 16px;
}
.identity-grid,
.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.identity-grid label,
.config-grid label,
.notes-field {
  display: grid;
  gap: 5px;
}
.identity-grid label > span,
.config-grid label > span,
.notes-field > span {
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 750;
}
.identity-name {
  grid-column: span 2;
}
.notes-field textarea {
  min-height: 76px;
  resize: vertical;
}
.stage-settings {
  display: grid;
  gap: 9px;
}
.stage-settings header h4 {
  margin: 0;
  font-size: 0.95rem;
}
.stage-settings header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
}
.stage-settings-card {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.stage-settings-heading {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}
.stage-settings-heading strong,
.stage-settings-heading code {
  display: block;
}
.stage-settings-heading strong {
  font-size: 0.82rem;
}
.stage-settings-heading code {
  margin-top: 2px;
  color: var(--muted);
  font-size: 0.72rem;
}
.stage-settings-heading > span {
  color: var(--muted);
  font-size: 0.7rem;
  font-weight: 700;
}
.no-config {
  margin: 0;
  color: var(--muted);
  font-size: 0.76rem;
}
@media (max-width: 680px) {
  .identity-grid,
  .config-grid {
    grid-template-columns: 1fr;
  }
  .identity-name {
    grid-column: auto;
  }
}
</style>

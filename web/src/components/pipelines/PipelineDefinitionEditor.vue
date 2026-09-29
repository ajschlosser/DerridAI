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
const stageIds = computed(() => props.modelValue.stages.map((stage) => stage.id));
const strategiesByFamily = computed(() => {
  const groups = new Map<string, PipelineStrategy[]>();
  for (const strategy of props.strategies) {
    const rows = groups.get(strategy.family) || [];
    rows.push(strategy);
    groups.set(strategy.family, rows);
  }
  return [...groups.entries()].map(([family, strategies]) => ({
    family,
    strategies: strategies.sort((a, b) => a.label.localeCompare(b.label)),
  }));
});

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
function replaceStageReference(value: string | null | undefined, from: string, to: string) {
  return value === from ? to : value;
}
function updateStageId(stageIndex: number, value: string) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;
  const previous = stage.id;
  const normalized = String(value || "").trim();
  stage.id = normalized;
  if (!previous || previous === normalized) {
    emit("update:modelValue", next);
    return;
  }

  next.entry_stage_ids = next.entry_stage_ids.map((id) => (id === previous ? normalized : id));
  for (const row of next.stages) {
    row.next = row.next.map((id) => (id === previous ? normalized : id));
    row.on_empty = replaceStageReference(row.on_empty, previous, normalized);
    row.on_unavailable = replaceStageReference(row.on_unavailable, previous, normalized);
    row.on_timeout = replaceStageReference(row.on_timeout, previous, normalized);
    row.on_error = replaceStageReference(row.on_error, previous, normalized);
  }
  emit("update:modelValue", next);
}
function updateStageStrategy(stageIndex: number, strategyId: string) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;
  stage.strategy = strategyId;
  // Configuration is schema-owned by the strategy. Carrying arbitrary keys
  // across a strategy switch is misleading and can alter runtime behavior.
  stage.config = {};
  emit("update:modelValue", next);
}
function toggleStageEnabled(stageIndex: number, enabled: boolean) {
  const next = clonePipeline();
  if (!next.stages[stageIndex]) return;
  next.stages[stageIndex].enabled = enabled;
  emit("update:modelValue", next);
}
function toggleEntry(stageId: string, checked: boolean) {
  const next = clonePipeline();
  const entries = new Set(next.entry_stage_ids);
  if (checked) entries.add(stageId);
  else if (entries.size > 1) entries.delete(stageId);
  next.entry_stage_ids = [...entries];
  emit("update:modelValue", next);
}
function toggleNext(stageIndex: number, targetId: string, checked: boolean) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;
  const edges = new Set(stage.next);
  checked ? edges.add(targetId) : edges.delete(targetId);
  stage.next = [...edges];
  emit("update:modelValue", next);
}
function updateFallback(
  stageIndex: number,
  key: "on_empty" | "on_unavailable" | "on_timeout" | "on_error",
  target: string,
) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;
  stage[key] = target || null;
  emit("update:modelValue", next);
}
function addStage() {
  const next = clonePipeline();
  const strategy = props.strategies[0];
  if (!strategy) return;
  const used = new Set(next.stages.map((stage) => stage.id));
  const stem = strategy.strategy_id.split(".").pop()?.replace(/[^a-z0-9_]+/gi, "_") || "stage";
  let suffix = next.stages.length + 1;
  let id = stem;
  while (used.has(id)) id = `${stem}_${suffix++}`;
  next.stages.push({
    id,
    strategy: strategy.strategy_id,
    enabled: true,
    config: {},
    next: [],
    on_empty: null,
    on_unavailable: null,
    on_timeout: null,
    on_error: null,
  });
  if (!next.entry_stage_ids.length) next.entry_stage_ids = [id];
  emit("update:modelValue", next);
}
function removeStage(stageIndex: number) {
  if (props.modelValue.stages.length <= 1) return;
  const next = clonePipeline();
  const [removed] = next.stages.splice(stageIndex, 1);
  if (!removed) return;
  next.entry_stage_ids = next.entry_stage_ids.filter((id) => id !== removed.id);
  for (const stage of next.stages) {
    stage.next = stage.next.filter((id) => id !== removed.id);
    for (const key of ["on_empty", "on_unavailable", "on_timeout", "on_error"] as const) {
      if (stage[key] === removed.id) stage[key] = null;
    }
  }
  if (!next.entry_stage_ids.length && next.stages.length) {
    next.entry_stage_ids = [next.stages[0].id];
  }
  emit("update:modelValue", next);
}
function moveStage(stageIndex: number, direction: -1 | 1) {
  const target = stageIndex + direction;
  if (target < 0 || target >= props.modelValue.stages.length) return;
  const next = clonePipeline();
  const [stage] = next.stages.splice(stageIndex, 1);
  next.stages.splice(target, 0, stage);
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
              :value="configValue(stage, key, rule)"
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

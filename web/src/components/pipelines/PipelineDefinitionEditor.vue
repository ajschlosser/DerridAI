<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import PipelineStageEditor from "./PipelineStageEditor.vue";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";

const props = defineProps<{
  modelValue: PipelineDefinition;
  strategies: PipelineStrategy[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: PipelineDefinition];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

function clonePipeline(): PipelineDefinition {
  return JSON.parse(JSON.stringify(props.modelValue)) as PipelineDefinition;
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
  // Configuration is owned by the registered strategy schema. Carrying keys
  // across a strategy switch can silently change runtime behavior.
  stage.config = {};
  emit("update:modelValue", next);
}

function toggleStageEnabled(stageIndex: number, enabled: boolean) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;
  stage.enabled = enabled;
  emit("update:modelValue", next);
}

function toggleEntry(stageId: string, checked: boolean) {
  const next = clonePipeline();
  const entries = new Set(next.entry_stage_ids);
  if (checked) {
    entries.add(stageId);
  } else if (entries.size > 1) {
    entries.delete(stageId);
  }
  next.entry_stage_ids = [...entries];
  emit("update:modelValue", next);
}

function toggleNext(stageIndex: number, targetId: string, checked: boolean) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;
  const edges = new Set(stage.next);
  if (checked) edges.add(targetId);
  else edges.delete(targetId);
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

function updateConfig(
  stageIndex: number,
  key: string,
  raw: string | boolean,
  rule: Record<string, unknown>,
) {
  const next = clonePipeline();
  const stage = next.stages[stageIndex];
  if (!stage) return;

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

function addStage() {
  const next = clonePipeline();
  const strategy =
    props.strategies.find((item) => item.strategy_id === "query.passthrough") ||
    props.strategies[0];
  if (!strategy) return;

  const used = new Set(next.stages.map((stage) => stage.id));
  const stem =
    strategy.strategy_id
      .split(".")
      .pop()
      ?.replace(/[^a-z0-9_]+/gi, "_") || "stage";
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
  if (!stage) return;
  next.stages.splice(target, 0, stage);
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
      <header class="stage-settings-header">
        <div>
          <h4>{{ t("pipelines.stage_settings", "Stage settings") }}</h4>
          <p>
            {{
              t(
                "pipelines.stage_settings_help",
                "Build the chain from registered strategies. Edges and fallback paths are validated before a version can be activated.",
              )
            }}
          </p>
        </div>
        <button class="btn" type="button" :disabled="!strategies.length" @click="addStage">
          {{ t("pipelines.add_stage", "Add stage") }}
        </button>
      </header>

      <PipelineStageEditor
        v-for="(stage, stageIndex) in modelValue.stages"
        :key="`${stage.id}:${stageIndex}`"
        :stage="stage"
        :stage-index="stageIndex"
        :stages="modelValue.stages"
        :strategies="strategies"
        :entry-stage-ids="modelValue.entry_stage_ids"
        @update-id="updateStageId"
        @update-strategy="updateStageStrategy"
        @update-enabled="toggleStageEnabled"
        @toggle-entry="toggleEntry"
        @move="moveStage"
        @remove="removeStage"
        @toggle-next="toggleNext"
        @update-fallback="updateFallback"
        @update-config="updateConfig"
      />
    </section>
  </div>
</template>

<style scoped>
.pipeline-editor {
  display: grid;
  gap: 16px;
}
.identity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.identity-grid label,
.notes-field {
  display: grid;
  gap: 5px;
}
.identity-grid label > span,
.notes-field > span {
  color: var(--muted);
  font-size: 0.75rem;
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
.stage-settings-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.stage-settings-header .btn {
  flex: 0 0 auto;
}
.stage-settings-header h4 {
  margin: 0;
  font-size: 0.95rem;
}
.stage-settings-header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
}
@media (max-width: 860px) {
  .stage-settings-header {
    display: grid;
  }
}
@media (max-width: 680px) {
  .identity-grid {
    grid-template-columns: 1fr;
  }
  .identity-name {
    grid-column: auto;
  }
}
</style>

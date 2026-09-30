<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import PipelineEditorVersionDetails from "./PipelineEditorVersionDetails.vue";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import PipelineStageEditor from "./PipelineStageEditor.vue";
import PipelineStageNavigator from "./PipelineStageNavigator.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  modelValue: PipelineDefinition;
  strategies: PipelineStrategy[];
  purpose?: PipelinePurpose | null;
  vocabulary?: PipelineWorkflowVocabulary;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: PipelineDefinition];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
// Operations the purpose's adapter cannot run stay reachable for inspect-only
// versions, but only behind this explicit choice.
const showAllStrategies = ref(false);
// Selection is by position so renaming a stage never loses it.
const selectedIndex = ref(0);
const stageEditor = ref<InstanceType<typeof PipelineStageEditor> | null>(null);
const selectedStage = computed(() => props.modelValue.stages[selectedIndex.value] || null);
const selectedStageId = computed(() => selectedStage.value?.id ?? "");

watch(
  () => props.modelValue.stages.length,
  (length) => {
    if (selectedIndex.value >= length) selectedIndex.value = Math.max(0, length - 1);
  },
);

function selectStageById(id: string) {
  const index = props.modelValue.stages.findIndex((stage) => stage.id === id);
  if (index >= 0) selectedIndex.value = index;
}

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
  selectedIndex.value = next.stages.length - 1;
  void nextTick(() => stageEditor.value?.focus());
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
  // The next stage takes the removed stage's place, else the previous one.
  selectedIndex.value = Math.min(stageIndex, Math.max(0, next.stages.length - 1));
}

function moveStage(stageIndex: number, direction: -1 | 1) {
  const target = stageIndex + direction;
  if (target < 0 || target >= props.modelValue.stages.length) return;
  const next = clonePipeline();
  const [stage] = next.stages.splice(stageIndex, 1);
  if (!stage) return;
  next.stages.splice(target, 0, stage);
  emit("update:modelValue", next);
  if (selectedIndex.value === stageIndex) selectedIndex.value = target;
  else if (selectedIndex.value === target) selectedIndex.value = stageIndex;
}
</script>

<template>
  <div class="pipeline-editor">
    <PipelineEditorVersionDetails
      :model-value="modelValue"
      @update="(key, value) => updateRoot(key, value as never)"
    />

    <div class="pipeline-editor-workspace">
      <div class="pipeline-editor-main">
        <PipelineGraphDiagram
          :stages="modelValue.stages"
          :entry-stage-ids="modelValue.entry_stage_ids"
          :strategies="strategies"
          :vocabulary="vocabulary"
          :title="t('pipelines.diagram_title', 'Pipeline diagram')"
          :description="
            t(
              'pipelines.editor_diagram_help',
              'Select a stage in the diagram or the list to edit it. Solid arrows are the normal path; dashed arrows are fallbacks.',
            )
          "
          :selected-stage-id="selectedStageId"
          :show-inspector="false"
          @update:selected-stage-id="selectStageById"
        />
        <PipelineStageNavigator
          :stages="modelValue.stages"
          :strategies="strategies"
          :selected-index="selectedIndex"
          :entry-stage-ids="modelValue.entry_stage_ids"
          :can-add="strategies.length > 0"
          @select="selectedIndex = $event"
          @add="addStage"
          @move="moveStage"
        />
      </div>

      <PipelineStageEditor
        v-if="selectedStage"
        ref="stageEditor"
        :stage="selectedStage"
        :stage-index="selectedIndex"
        :stages="modelValue.stages"
        :strategies="strategies"
        :purpose="purpose || null"
        :vocabulary="vocabulary"
        :show-all-strategies="showAllStrategies"
        :entry-stage-ids="modelValue.entry_stage_ids"
        @update-id="updateStageId"
        @update-strategy="updateStageStrategy"
        @update-enabled="toggleStageEnabled"
        @toggle-entry="toggleEntry"
        @remove="removeStage"
        @update:show-all-strategies="showAllStrategies = $event"
        @toggle-next="toggleNext"
        @update-fallback="updateFallback"
        @update-config="updateConfig"
      />
    </div>
  </div>
</template>

<style scoped>
.pipeline-editor {
  display: grid;
  gap: var(--space-4);
}
.pipeline-editor-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 380px);
  gap: var(--space-4);
  align-items: start;
}
.pipeline-editor-main {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
@media (max-width: 1100px) {
  .pipeline-editor-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

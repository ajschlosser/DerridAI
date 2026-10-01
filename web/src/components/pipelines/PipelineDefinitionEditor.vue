<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import PipelineAnalysisPanel from "./PipelineAnalysisPanel.vue";
import PipelineEditorVersionDetails from "./PipelineEditorVersionDetails.vue";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import PipelineStageEditor from "./PipelineStageEditor.vue";
import PipelineStageNavigator from "./PipelineStageNavigator.vue";
import PipelineStagePalette from "./PipelineStagePalette.vue";
import PipelineTypeChip from "./PipelineTypeChip.vue";
import {
  lensBadges,
  stagesWithWiringProblems,
  type DiagramLens,
} from "../../domain/pipelineAnalysisPresentation";
import {
  clearStageBindings,
  insertStage,
  removeBindingReferences,
  renameBindingReferences,
  bindInput as applyBinding,
  releaseOrderingEdges,
  type OrderingEdge,
  type BindingChoice,
  type InsertMode,
} from "../../domain/pipelineBindings";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAnalysis,
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineStrategyLatency,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  modelValue: PipelineDefinition;
  strategies: PipelineStrategy[];
  purpose?: PipelinePurpose | null;
  vocabulary?: PipelineWorkflowVocabulary;
  /** Server analysis of this draft; undefined hides the wiring and performance panels. */
  analysis?: PipelineAnalysis | null;
  analysisLoading?: boolean;
  analysisError?: string;
  strategyLatency?: Record<string, PipelineStrategyLatency> | null;
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
const paletteOpen = ref(false);
const lens = ref<DiagramLens>("structure");
const bindNotice = ref("");
const selectedStrategy = computed(
  () => props.strategies.find((item) => item.strategy_id === selectedStage.value?.strategy) ?? null,
);
const badges = computed(() => lensBadges(props.analysis ?? null, lens.value, t));
const flaggedStageIds = computed(() => [...stagesWithWiringProblems(props.analysis ?? null)]);
const lensOptions = computed<Array<{ id: DiagramLens; label: string }>>(() => [
  { id: "structure", label: t("pipelines.lens_structure", "Structure") },
  { id: "latency", label: t("pipelines.lens_latency", "Latency") },
  { id: "complexity", label: t("pipelines.lens_complexity", "Complexity") },
]);

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
  renameBindingReferences(next, previous, normalized);
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
  // across a strategy switch can silently change runtime behavior. The same
  // goes for input bindings: ports belong to the strategy.
  stage.config = {};
  clearStageBindings(stage);
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

function openPalette() {
  paletteOpen.value = true;
}

function addFromPalette(strategyId: string, mode: InsertMode) {
  const result = insertStage(
    props.modelValue,
    strategyId,
    mode === "entry" ? null : selectedStageId.value || null,
    mode,
  );
  paletteOpen.value = false;
  emit("update:modelValue", result.pipeline);
  selectedIndex.value = result.pipeline.stages.length - 1;
  void nextTick(() => stageEditor.value?.focus());
}

// Edges this editor added only to order a producer ahead of a bound consumer.
const orderingEdges: OrderingEdge[] = [];

function bindInput(stageIndex: number, port: string, choice: BindingChoice | null) {
  const stage = props.modelValue.stages[stageIndex];
  if (!stage) return;
  const result = applyBinding(props.modelValue, stage.id, port, choice);
  if (!result) {
    bindNotice.value = t(
      "pipelines.ports_cycle",
      "That stage runs after this one, so it cannot feed it. Choose an earlier stage.",
    );
    return;
  }
  bindNotice.value = "";
  let next = result.pipeline;
  if (result.added) orderingEdges.push(result.added);
  if (choice === null) {
    const released = releaseOrderingEdges(next, orderingEdges, stage.id);
    next = released.pipeline;
    orderingEdges.splice(0, orderingEdges.length, ...released.tracked);
  }
  emit("update:modelValue", next);
}

function removeStage(stageIndex: number) {
  if (props.modelValue.stages.length <= 1) return;
  const next = clonePipeline();
  const [removed] = next.stages.splice(stageIndex, 1);
  if (!removed) return;

  next.entry_stage_ids = next.entry_stage_ids.filter((id) => id !== removed.id);
  removeBindingReferences(next, removed.id);
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
        <ul
          v-if="analysis?.wiring.run_inputs.length"
          class="run-inputs"
          :aria-label="t('pipelines.run_inputs_label', 'Inputs the workflow supplies')"
        >
          <li v-for="input in analysis.wiring.run_inputs" :key="input.name">
            <span class="run-inputs-kicker">{{
              t("pipelines.run_inputs_kicker", "Workflow supplies")
            }}</span>
            <code>{{ input.name }}</code>
            <PipelineTypeChip :type="input.data_type" />
            <span class="run-inputs-uses">
              {{
                input.consumers.length
                  ? input.consumers.map((use) => `${use.stage}.${use.port}`).join(", ")
                  : t("pipelines.ports_unused", "Not used by any stage.")
              }}
            </span>
          </li>
        </ul>
        <div
          v-if="analysis !== undefined"
          class="lens"
          role="group"
          :aria-label="t('pipelines.lens_label', 'What the diagram shows on each stage')"
        >
          <button
            v-for="option in lensOptions"
            :key="option.id"
            type="button"
            class="lens-option"
            :aria-pressed="lens === option.id"
            @click="lens = option.id"
          >
            {{ option.label }}
          </button>
        </div>
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
          :badges="badges"
          :flagged-stage-ids="flaggedStageIds"
          @update:selected-stage-id="selectStageById"
        />
        <PipelineStageNavigator
          :stages="modelValue.stages"
          :strategies="strategies"
          :selected-index="selectedIndex"
          :entry-stage-ids="modelValue.entry_stage_ids"
          :can-add="strategies.length > 0"
          @select="selectedIndex = $event"
          @add="openPalette"
          @move="moveStage"
        />
        <PipelineAnalysisPanel
          v-if="analysis !== undefined"
          :analysis="analysis"
          :loading="analysisLoading"
          :error="analysisError"
          :strategies="strategies"
          :vocabulary="vocabulary"
          :selected-stage-id="selectedStageId"
          @select-stage="selectStageById"
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
        :wiring="analysis?.wiring.stages[selectedStage.id] ?? null"
        :wiring-loading="analysisLoading"
        :wiring-error="bindNotice || analysisError"
        @bind-input="bindInput"
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

    <PipelineStagePalette
      v-if="paletteOpen"
      :strategies="strategies"
      :purpose="purpose || null"
      :vocabulary="vocabulary"
      :anchor="selectedStage"
      :anchor-strategy="selectedStrategy"
      :latency="strategyLatency"
      @close="paletteOpen = false"
      @add="addFromPalette"
    />
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
.run-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.run-inputs li {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  font-size: 0.8125rem;
}
.run-inputs-kicker {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.run-inputs-uses {
  color: var(--text-secondary);
}
.lens {
  display: inline-flex;
  justify-self: start;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  overflow: hidden;
}
.lens-option {
  min-height: var(--control-height);
  padding: 4px 14px;
  border: 0;
  background: var(--surface-card);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 750;
  cursor: pointer;
}
.lens-option + .lens-option {
  border-inline-start: 1px solid var(--border-subtle);
}
.lens-option[aria-pressed="true"] {
  background: var(--ui-accent-soft);
  color: var(--accent-fg);
}
.lens-option:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: calc(var(--focus-ring-offset) * -1);
}
@media (max-width: 1100px) {
  .pipeline-editor-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

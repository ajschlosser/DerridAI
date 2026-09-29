<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import PipelineStageConnections from "./PipelineStageConnections.vue";
import PipelineStrategyConfigFields from "./PipelineStrategyConfigFields.vue";
import {
  pipelineDataTypeHelp,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineStage, PipelineStrategy } from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  stage: PipelineStage;
  stageIndex: number;
  stages: PipelineStage[];
  strategies: PipelineStrategy[];
  entryStageIds: string[];
}>();

const emit = defineEmits<{
  updateId: [stageIndex: number, value: string];
  updateStrategy: [stageIndex: number, strategyId: string];
  updateEnabled: [stageIndex: number, enabled: boolean];
  toggleEntry: [stageId: string, checked: boolean];
  move: [stageIndex: number, direction: -1 | 1];
  remove: [stageIndex: number];
  toggleNext: [stageIndex: number, targetId: string, checked: boolean];
  updateFallback: [
    stageIndex: number,
    key: "on_empty" | "on_unavailable" | "on_timeout" | "on_error",
    target: string,
  ];
  updateConfig: [
    stageIndex: number,
    key: string,
    raw: string | boolean,
    rule: Record<string, unknown>,
  ];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const strategy = computed(
  () => props.strategies.find((item) => item.strategy_id === props.stage.strategy) || null,
);
const strategiesByFamily = computed(() => {
  const groups = new Map<string, PipelineStrategy[]>();
  for (const item of props.strategies) {
    const rows = groups.get(item.family) || [];
    rows.push(item);
    groups.set(item.family, rows);
  }
  return [...groups.entries()].map(([family, strategies]) => ({
    family,
    strategies: [...strategies].sort((a, b) =>
      pipelineStrategyLabel(a, t).localeCompare(pipelineStrategyLabel(b, t), i18n.locale),
    ),
  }));
});
</script>

<template>
  <article class="stage-settings-card">
    <div class="stage-settings-heading">
      <div class="stage-identity-grid">
        <label>
          <span class="label-with-help">
            {{ t("pipelines.stage_id", "Stage ID") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.stage_id_help',
                  'A short internal name for this step. Other stages use this name when they point to it. Renaming it here also updates those connections.',
                )
              "
            />
          </span>
          <input
            class="control"
            :value="stage.id"
            autocomplete="off"
            @input="emit('updateId', stageIndex, ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label>
          <span class="label-with-help">
            {{ t("pipelines.strategy", "Strategy") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.strategy_help',
                  'The strategy is the server-approved operation this stage performs—for example semantic retrieval, reranking, provenance checking, or answer generation. You are choosing among registered operations, not writing executable code.',
                )
              "
            />
          </span>
          <select
            class="control"
            :value="stage.strategy"
            @change="emit('updateStrategy', stageIndex, ($event.target as HTMLSelectElement).value)"
          >
            <optgroup
              v-for="group in strategiesByFamily"
              :key="group.family"
              :label="pipelineStageFamilyLabel(group.family, t)"
            >
              <option
                v-for="option in group.strategies"
                :key="option.strategy_id"
                :value="option.strategy_id"
              >
                {{ pipelineStrategyLabel(option, t) }}
              </option>
            </optgroup>
          </select>
        </label>
      </div>

      <div class="stage-toolbar">
        <label class="stage-toggle">
          <input
            type="checkbox"
            :checked="stage.enabled"
            @change="emit('updateEnabled', stageIndex, ($event.target as HTMLInputElement).checked)"
          />
          <span class="toggle-copy">
            {{ t("pipelines.enabled", "Enabled") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.enabled_help',
                  'When disabled, this stage remains in the saved definition for reference but is not part of the executable graph.',
                )
              "
            />
          </span>
        </label>
        <label class="stage-toggle">
          <input
            type="checkbox"
            :checked="entryStageIds.includes(stage.id)"
            @change="emit('toggleEntry', stage.id, ($event.target as HTMLInputElement).checked)"
          />
          <span class="toggle-copy">
            {{ t("pipelines.entry_stage", "Entry") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.entry_stage_help',
                  'An entry stage is where execution starts. Most Research pipelines have one entry step, usually a query-analysis step; some graph types may allow more than one.',
                )
              "
            />
          </span>
        </label>
        <button
          class="btn icon-only"
          type="button"
          :disabled="stageIndex === 0"
          :aria-label="t('pipelines.move_stage_up', 'Move stage up')"
          @click="emit('move', stageIndex, -1)"
        >
          ↑
        </button>
        <button
          class="btn icon-only"
          type="button"
          :disabled="stageIndex === stages.length - 1"
          :aria-label="t('pipelines.move_stage_down', 'Move stage down')"
          @click="emit('move', stageIndex, 1)"
        >
          ↓
        </button>
        <button
          class="btn icon-only"
          type="button"
          :disabled="stages.length <= 1"
          :aria-label="t('pipelines.remove_stage', 'Remove stage')"
          @click="emit('remove', stageIndex)"
        >
          ×
        </button>
      </div>
    </div>

    <div class="strategy-summary">
      <div>
        <strong>{{ strategy ? pipelineStrategyLabel(strategy, t) : stage.strategy }}</strong>
        <span>{{ pipelineStageFamilyLabel(strategy?.family, t) }}</span>
      </div>
      <p v-if="strategy">{{ pipelineStrategyDescription(strategy, t) }}</p>
      <small v-if="strategy" class="strategy-io">
        <span>
          {{ t("pipelines.input", "Input") }}: <code>{{ strategy.input_type }}</code>
          <UiTooltip
            :text="pipelineDataTypeHelp(strategy.input_type, t)"
            :label="t('pipelines.explain_input_type', 'Explain this input type')"
          />
        </span>
        <span aria-hidden="true">→</span>
        <span>
          {{ t("pipelines.output", "Output") }}: <code>{{ strategy.output_type }}</code>
          <UiTooltip
            :text="pipelineDataTypeHelp(strategy.output_type, t)"
            :label="t('pipelines.explain_output_type', 'Explain this output type')"
          />
        </span>
        <span v-if="strategy.invokes_llm">
          {{ t("pipelines.invokes_llm", "Uses a language model") }}
          <UiTooltip
            :text="
              t(
                'pipelines.invokes_llm_help',
                'This stage calls a configured language model. Its output may vary between runs, so DerridAI records the model and execution trace for auditability.',
              )
            "
          />
        </span>
        <span v-else>
          {{ t("pipelines.deterministic", "Deterministic") }}
          <UiTooltip
            :text="
              t(
                'pipelines.deterministic_help',
                'This stage follows fixed program logic rather than asking a language model to decide the result. The same inputs and configuration should produce the same result.',
              )
            "
          />
        </span>
      </small>
    </div>

    <PipelineStageConnections
      :stage="stage"
      :stages="stages"
      @toggle-next="(targetId, checked) => emit('toggleNext', stageIndex, targetId, checked)"
      @update-fallback="(key, target) => emit('updateFallback', stageIndex, key, target)"
    />

    <PipelineStrategyConfigFields
      :stage="stage"
      :strategy="strategy"
      @update-config="(key, raw, rule) => emit('updateConfig', stageIndex, key, raw, rule)"
    />
  </article>
</template>

<style scoped>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.stage-identity-grid {
  display: grid;
  grid-template-columns: minmax(10rem, 0.75fr) minmax(14rem, 1.25fr);
  gap: 10px;
  flex: 1;
}
.stage-identity-grid label {
  display: grid;
  gap: 5px;
}
.stage-identity-grid label > span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.label-with-help,
.toggle-copy,
.strategy-io > span {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.strategy-io {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
}
.strategy-io code {
  font-size: 0.72rem;
}
.stage-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: flex-end;
}
.stage-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 36px;
  padding: 0 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  font-size: 0.75rem;
  font-weight: 700;
}
.stage-toggle input {
  margin: 0;
}
.strategy-summary {
  display: grid;
  gap: 4px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
}
.strategy-summary > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.strategy-summary strong {
  font-size: 0.78rem;
}
.strategy-summary span,
.strategy-summary p,
.strategy-summary small {
  color: var(--muted);
}
.strategy-summary > div span,
.strategy-summary p,
.strategy-summary small {
  font-size: 0.75rem;
}
.strategy-summary > div span {
  font-weight: 700;
}
.strategy-summary p,
.strategy-summary small {
  margin: 0;
  line-height: 1.4;
}
@media (max-width: 860px) {
  .stage-settings-heading {
    display: grid;
  }
  .stage-toolbar {
    justify-content: flex-start;
  }
}
@media (max-width: 680px) {
  .stage-identity-grid {
    grid-template-columns: 1fr;
  }
}
</style>

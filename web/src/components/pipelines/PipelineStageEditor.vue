<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import PipelineStageConnections from "./PipelineStageConnections.vue";
import PipelineStrategyConfigFields from "./PipelineStrategyConfigFields.vue";
import UiButton from "../ui/UiButton.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import {
  pipelineCapabilityLabel,
  pipelineComputationLabel,
  pipelineDataTypeHelp,
  pipelineDataTypeLabel,
  pipelineStageFamilyHelp,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import {
  findTerm,
  purposeText,
  strategyComputation,
  strategyPickerGroups,
  termLabel,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelinePurpose,
  PipelineStage,
  PipelineStrategy,
  PipelineStrategyFit,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  stage: PipelineStage;
  stageIndex: number;
  stages: PipelineStage[];
  strategies: PipelineStrategy[];
  entryStageIds: string[];
  /** The pipeline's purpose; its adapter decides which strategies are supported. */
  purpose?: PipelinePurpose | null;
  showAllStrategies?: boolean;
  vocabulary?: PipelineWorkflowVocabulary;
}>();

const emit = defineEmits<{
  updateId: [stageIndex: number, value: string];
  updateStrategy: [stageIndex: number, strategyId: string];
  updateEnabled: [stageIndex: number, enabled: boolean];
  toggleEntry: [stageId: string, checked: boolean];
  remove: [stageIndex: number];
  "update:showAllStrategies": [value: boolean];
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
const heading = ref<HTMLElement | null>(null);
const strategy = computed(
  () => props.strategies.find((item) => item.strategy_id === props.stage.strategy) || null,
);
const effectNote = computed(() => {
  const term = findTerm(props.vocabulary?.effect_notes, strategy.value?.effect_note);
  return term ? termLabel(term, t) : "";
});
function byFamilyThenLabel(rows: PipelineStrategy[]) {
  return [...rows].sort(
    (a, b) =>
      a.family.localeCompare(b.family) ||
      pipelineStrategyLabel(a, t).localeCompare(pipelineStrategyLabel(b, t), i18n.locale),
  );
}
function optionText(item: PipelineStrategy) {
  return `${pipelineStrategyLabel(item, t)} · ${pipelineStageFamilyLabel(item.family, t)}`;
}
const fit = computed<PipelineStrategyFit>(() =>
  props.purpose ? props.purpose.strategy_fit[props.stage.strategy] || "inspect_only" : "supported",
);
const purposeLabel = computed(() => (props.purpose ? purposeText(props.purpose, "label", t) : ""));
const optionGroups = computed(() => {
  if (!props.purpose) {
    return [
      {
        id: "all",
        label: t("pipelines.strategy_group_all", "Registered operations"),
        disabled: false,
        strategies: byFamilyThenLabel(props.strategies),
      },
    ];
  }
  const groups = strategyPickerGroups(props.strategies, props.purpose);
  // The stage's current strategy always stays listed so the select can show it.
  const keep = (rows: PipelineStrategy[]) =>
    props.showAllStrategies ? rows : rows.filter((row) => row.strategy_id === props.stage.strategy);
  return [
    {
      id: "supported",
      label: t("pipelines.strategy_group_supported", "Supported for this workflow"),
      disabled: false,
      strategies: byFamilyThenLabel(groups.supported),
    },
    {
      id: "inspect_only",
      label: t("pipelines.strategy_group_inspect_only", "Other operations — inspect only"),
      disabled: false,
      strategies: byFamilyThenLabel(keep(groups.inspect_only)),
    },
    {
      id: "output_contract",
      label: t(
        "pipelines.strategy_group_output_contract",
        "Unsupported — changes this workflow’s output",
      ),
      disabled: true,
      strategies: byFamilyThenLabel(keep(groups.output_contract)),
    },
  ].filter((group) => group.strategies.length);
});
const fitNote = computed(() => {
  if (!props.purpose || fit.value === "supported") return "";
  if (fit.value === "output_contract") {
    return i18n.tf(
      "pipelines.strategy_fit_output_contract",
      "{strategy} produces {output}, but a {purpose} pipeline must return {contract}. This version cannot run.",
      {
        strategy: strategy.value ? pipelineStrategyLabel(strategy.value, t) : props.stage.strategy,
        output: pipelineDataTypeLabel(strategy.value?.output_type || "", t),
        purpose: purposeLabel.value,
        contract: pipelineDataTypeLabel(props.purpose.output_type, t),
      },
    );
  }
  return i18n.tf(
    "pipelines.strategy_fit_inspect_only",
    "{strategy} is not run by the {purpose} adapter. A version that uses it stays inspect-only.",
    {
      strategy: strategy.value ? pipelineStrategyLabel(strategy.value, t) : props.stage.strategy,
      purpose: purposeLabel.value,
    },
  );
});

defineExpose({ focus: () => heading.value?.focus() });
</script>

<template>
  <aside class="stage-inspector-editor" :aria-labelledby="`stage-editor-title-${stageIndex}`">
    <p class="editor-kicker">{{ t("pipelines.stage", "Stage") }}</p>
    <h4 :id="`stage-editor-title-${stageIndex}`" ref="heading" tabindex="-1">
      {{ stage.id || t("pipelines.unnamed_stage", "Unnamed stage") }}
    </h4>

    <label class="field">
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

    <div class="field">
      <label class="field-label label-with-help" :for="`stage-strategy-${stageIndex}`">
        {{ t("pipelines.strategy", "Strategy") }}
        <UiTooltip
          :text="
            t(
              'pipelines.strategy_help',
              'The strategy is the server-approved operation this stage performs—for example semantic retrieval, reranking, provenance checking, or answer generation. You are choosing among registered operations, not writing executable code.',
            )
          "
        />
      </label>
      <select
        :id="`stage-strategy-${stageIndex}`"
        class="control"
        :value="stage.strategy"
        :aria-describedby="fitNote ? `stage-fit-${stageIndex}` : undefined"
        @change="emit('updateStrategy', stageIndex, ($event.target as HTMLSelectElement).value)"
      >
        <optgroup
          v-for="group in optionGroups"
          :key="group.id"
          :label="group.label"
          :data-fit="group.id"
        >
          <option
            v-for="option in group.strategies"
            :key="option.strategy_id"
            :value="option.strategy_id"
            :disabled="group.disabled && option.strategy_id !== stage.strategy"
          >
            {{ optionText(option) }}
          </option>
        </optgroup>
      </select>
      <small
        v-if="fitNote"
        :id="`stage-fit-${stageIndex}`"
        class="stage-fit-note"
        :data-fit="fit"
        role="note"
      >
        {{ fitNote }}
      </small>
      <small class="field-help">
        {{
          t(
            "pipelines.strategy_safety_summary",
            "Strategies are registered server operations; choosing one does not add executable code.",
          )
        }}
      </small>
      <details v-if="purpose" class="strategy-advanced">
        <summary>{{ t("pipelines.strategy_advanced", "Advanced") }}</summary>
        <label class="show-all-strategies">
          <input
            type="checkbox"
            :checked="showAllStrategies"
            @change="emit('update:showAllStrategies', ($event.target as HTMLInputElement).checked)"
          />
          <span>
            {{ t("pipelines.show_all_strategies", "Show operations this workflow cannot run") }}
            <small>
              {{
                t(
                  "pipelines.show_all_strategies_help",
                  "Saving a version that uses one keeps it inspect-only: it can be viewed and compared but not made active.",
                )
              }}
            </small>
          </span>
        </label>
      </details>
    </div>

    <div class="stage-toggles">
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
    </div>

    <section v-if="strategy" class="strategy-summary" aria-labelledby="stage-strategy-summary">
      <h5 id="stage-strategy-summary">{{ pipelineStrategyLabel(strategy, t) }}</h5>
      <p class="summary-family label-with-help">
        {{ pipelineStageFamilyLabel(strategy.family, t) }}
        <UiTooltip
          :text="pipelineStageFamilyHelp(strategy.family, t)"
          :label="t('pipelines.explain_stage_family', 'Explain this kind of stage')"
        />
      </p>
      <p>{{ pipelineStrategyDescription(strategy, t) }}</p>
      <dl>
        <div>
          <dt>{{ t("pipelines.strategy_io", "Input → output") }}</dt>
          <dd>
            <span class="label-with-help">
              {{ pipelineDataTypeLabel(strategy.input_type, t) }}
              <UiTooltip
                :text="pipelineDataTypeHelp(strategy.input_type, t)"
                :label="t('pipelines.explain_input_type', 'Explain this input type')"
              />
            </span>
            →
            <span class="label-with-help">
              {{ pipelineDataTypeLabel(strategy.output_type, t) }}
              <UiTooltip
                :text="pipelineDataTypeHelp(strategy.output_type, t)"
                :label="t('pipelines.explain_output_type', 'Explain this output type')"
              />
            </span>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_computation", "Computation") }}</dt>
          <dd>{{ pipelineComputationLabel(strategyComputation(strategy), t) }}</dd>
        </div>
        <div v-if="effectNote">
          <dt>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</dt>
          <dd>{{ effectNote }}</dd>
        </div>
        <div v-if="strategy.capabilities.length">
          <dt>{{ t("pipelines.strategy_requires", "Requires") }}</dt>
          <dd>
            {{ strategy.capabilities.map((item) => pipelineCapabilityLabel(item, t)).join(", ") }}
          </dd>
        </div>
      </dl>
    </section>

    <PipelineStageConnections
      :stage="stage"
      :stages="stages"
      @toggle-next="(targetId, checked) => emit('toggleNext', stageIndex, targetId, checked)"
      @update-fallback="(key, target) => emit('updateFallback', stageIndex, key, target)"
    />

    <section class="stage-config" aria-labelledby="stage-config-title">
      <h5 id="stage-config-title">{{ t("pipelines.stage_configuration", "Configuration") }}</h5>
      <PipelineStrategyConfigFields
        :stage="stage"
        :strategy="strategy"
        @update-config="(key, raw, rule) => emit('updateConfig', stageIndex, key, raw, rule)"
      />
    </section>

    <footer class="stage-footer">
      <UiButton
        variant="danger"
        :label="t('pipelines.remove_stage', 'Remove stage')"
        :disabled="stages.length <= 1"
        :disabled-reason="
          stages.length <= 1
            ? t('pipelines.remove_last_stage_reason', 'A pipeline needs at least one stage.')
            : ''
        "
        @click="emit('remove', stageIndex)"
      />
    </footer>
  </aside>
</template>

<style scoped>
.stage-inspector-editor {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.editor-kicker {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.stage-inspector-editor h4 {
  margin: calc(var(--space-3) * -1) 0 0;
  color: var(--text-primary);
  font-size: 1.125rem;
  overflow-wrap: anywhere;
}
.stage-inspector-editor h4:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.stage-inspector-editor h5 {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.9375rem;
}
.field {
  display: grid;
  gap: var(--space-1);
}
.field > span,
.field-label {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.field .control {
  width: 100%;
}
.field-help {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.stage-fit-note {
  display: block;
  padding: var(--space-1) var(--space-2);
  border-left: 3px solid var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.stage-fit-note[data-fit="output_contract"] {
  border-left-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.strategy-advanced summary {
  width: fit-content;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  cursor: pointer;
}
.strategy-advanced summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.show-all-strategies {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-2);
  font-size: 0.875rem;
}
.show-all-strategies input {
  margin-top: 3px;
}
.show-all-strategies small {
  display: block;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.label-with-help,
.toggle-copy {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.stage-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.stage-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-height-small);
  padding: 0 var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
}
.stage-toggle input {
  margin: 0;
}
.strategy-summary {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.strategy-summary p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.strategy-summary .summary-family {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.strategy-summary dl {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}
.strategy-summary dt {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.strategy-summary dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
}
.stage-config {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.stage-footer {
  display: flex;
  justify-content: flex-start;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
@media (min-width: 1101px) {
  .stage-inspector-editor {
    position: sticky;
    top: var(--pipeline-studio-sticky-top, var(--space-3));
    max-height: var(
      --pipeline-studio-pane-max-height,
      calc(100dvh - var(--pipeline-studio-sticky-top, var(--space-3)) - var(--space-3))
    );
    overflow: auto;
    overscroll-behavior: contain;
  }
}
</style>

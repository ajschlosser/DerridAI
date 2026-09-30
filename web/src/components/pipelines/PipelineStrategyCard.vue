<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import {
  pipelineCapabilityLabel,
  pipelineComputationLabel,
  pipelineDataTypeLabel,
  pipelineKey,
  pipelineStageFamilyHelp,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import {
  findTerm,
  purposeLabelFor,
  strategyComputation,
  termDescription,
  termLabel,
  type StrategyUsage,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  strategy: PipelineStrategy;
  usage: StrategyUsage;
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  selected?: boolean;
}>();

const emit = defineEmits<{
  select: [strategyId: string];
  openPipeline: [key: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const headingId = computed(() => `strategy-${props.strategy.strategy_id.replaceAll(".", "-")}`);
const effect = computed(() =>
  findTerm(props.vocabulary.scholarly_effects, props.strategy.scholarly_effect),
);
const note = computed(() => findTerm(props.vocabulary.effect_notes, props.strategy.effect_note));
const categories = computed(() =>
  props.usage.categories
    .map((id) => findTerm(props.vocabulary.categories, id))
    .filter((term) => term !== null),
);
// Opening the technical details makes this the URL-addressable strategy.
function onTechnicalToggle(event: Event) {
  if ((event.target as HTMLDetailsElement).open && !props.selected) {
    emit("select", props.strategy.strategy_id);
  }
}
const configKeys = computed(() => {
  const properties = (props.strategy.config_schema as { properties?: Record<string, unknown> })
    .properties;
  return Object.keys(properties || {});
});
</script>

<template>
  <article
    class="strategy-card"
    :class="{ selected }"
    :data-strategy="strategy.strategy_id"
    :aria-labelledby="headingId"
  >
    <header class="strategy-heading">
      <div>
        <h4 :id="headingId">{{ pipelineStrategyLabel(strategy, t) }}</h4>
        <code>{{ strategy.strategy_id }}</code>
      </div>
      <span v-if="note" class="effect-note" :data-effect="strategy.scholarly_effect">
        {{ termLabel(note, t) }}
      </span>
    </header>

    <p class="strategy-description">{{ pipelineStrategyDescription(strategy, t) }}</p>

    <dl class="strategy-facts">
      <div>
        <dt>{{ t("pipelines.strategy_family", "Family") }}</dt>
        <dd class="with-help">
          {{ pipelineStageFamilyLabel(strategy.family, t) }}
          <UiTooltip
            :text="pipelineStageFamilyHelp(strategy.family, t)"
            :label="t('pipelines.explain_stage_family', 'Explain this kind of stage')"
          />
        </dd>
      </div>
      <div>
        <dt>{{ t("pipelines.strategy_input_output", "Input → output") }}</dt>
        <dd>
          {{ pipelineDataTypeLabel(strategy.input_type, t) }}
          <span aria-hidden="true">→</span>
          <span class="sr-only">{{ t("pipelines.to", "to") }}</span>
          {{ pipelineDataTypeLabel(strategy.output_type, t) }}
        </dd>
      </div>
      <div>
        <dt>{{ t("pipelines.strategy_computation", "Computation") }}</dt>
        <dd>{{ pipelineComputationLabel(strategyComputation(strategy), t) }}</dd>
      </div>
      <div>
        <dt>{{ t("pipelines.strategy_requires", "Requires") }}</dt>
        <dd>
          {{
            strategy.capabilities.length
              ? strategy.capabilities.map((item) => pipelineCapabilityLabel(item, t)).join(", ")
              : t("pipelines.strategy_requires_nothing", "No external model or service")
          }}
        </dd>
      </div>
      <div v-if="effect">
        <dt>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</dt>
        <dd class="with-help">
          {{ termLabel(effect, t) }}
          <UiTooltip
            :text="termDescription(effect, t)"
            :label="t('pipelines.explain_scholarly_effect', 'Explain this scholarly effect')"
          />
        </dd>
      </div>
      <div>
        <dt>{{ t("pipelines.strategy_used_by", "Used by") }}</dt>
        <dd>
          {{
            categories.length
              ? categories.map((term) => termLabel(term, t)).join(", ")
              : t("pipelines.strategy_unused", "No current pipeline")
          }}
        </dd>
      </div>
    </dl>

    <details v-if="usage.pipelines.length" class="strategy-usage">
      <summary>
        {{
          i18n.tf("pipelines.strategy_pipeline_count", "Pipelines using this strategy: {count}", {
            count: usage.pipelines.length,
          })
        }}
      </summary>
      <ul>
        <li v-for="pipeline in usage.pipelines" :key="pipelineKey(pipeline)">
          <button
            type="button"
            class="link-button"
            @click="emit('openPipeline', pipelineKey(pipeline))"
          >
            {{ pipeline.name }}
          </button>
          <span class="usage-meta">
            {{ purposeLabelFor(purposes, pipeline.purpose, t) }} · v{{ pipeline.version }}
          </span>
        </li>
      </ul>
    </details>

    <details class="strategy-technical" :open="selected" @toggle="onTechnicalToggle">
      <summary>{{ t("pipelines.strategy_technical", "Technical details") }}</summary>
      <dl class="strategy-facts">
        <div>
          <dt>{{ t("pipelines.strategy_id", "Strategy ID") }}</dt>
          <dd>
            <code>{{ strategy.strategy_id }}</code> v{{ strategy.version }}
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_types", "Data types") }}</dt>
          <dd>
            <code>{{ strategy.input_type }}</code> → <code>{{ strategy.output_type }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_capabilities", "Capabilities") }}</dt>
          <dd>
            <code v-for="item in strategy.capabilities" :key="item">{{ item }}</code>
            <span v-if="!strategy.capabilities.length">—</span>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_settings", "Settings") }}</dt>
          <dd>
            <code v-for="key in configKeys" :key="key">{{ key }}</code>
            <span v-if="!configKeys.length">—</span>
          </dd>
        </div>
      </dl>
    </details>
  </article>
</template>

<style scoped>
.strategy-card {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.strategy-card.selected {
  border-color: currentColor;
}
.strategy-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px 12px;
}
.strategy-heading h4 {
  margin: 0;
  font-size: 0.86rem;
}
.strategy-heading code {
  color: var(--muted);
  font-size: 0.75rem;
}
.effect-note {
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}
.effect-note[data-effect="eligibility_gate"],
.effect-note[data-effect="provenance_gate"] {
  border-color: currentColor;
}
.strategy-description {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.strategy-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 6px 14px;
  margin: 0;
}
.strategy-facts > div {
  display: grid;
  gap: 1px;
  min-width: 0;
}
.strategy-facts dt {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.strategy-facts dd {
  margin: 0;
  font-size: 0.78rem;
  overflow-wrap: anywhere;
}
.strategy-facts dd code + code {
  margin-left: 6px;
}
.with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.strategy-usage summary,
.strategy-technical summary {
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}
.strategy-usage summary:focus-visible,
.strategy-technical summary:focus-visible,
.link-button:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
.strategy-usage ul {
  display: grid;
  gap: 4px;
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}
.strategy-usage li {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  font-size: 0.78rem;
}
.strategy-technical .strategy-facts {
  margin-top: 6px;
}
.link-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  text-decoration: underline;
  cursor: pointer;
}
.usage-meta {
  color: var(--muted);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>

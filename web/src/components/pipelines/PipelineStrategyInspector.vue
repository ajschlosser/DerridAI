<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import UiTooltip from "../ui/UiTooltip.vue";
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

const props = defineProps<{
  strategy: PipelineStrategy;
  usage: StrategyUsage;
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const effect = computed(() =>
  findTerm(props.vocabulary.scholarly_effects, props.strategy.scholarly_effect),
);
const note = computed(() => findTerm(props.vocabulary.effect_notes, props.strategy.effect_note));
const categories = computed(() =>
  props.usage.categories
    .map((id) => findTerm(props.vocabulary.categories, id))
    .filter((term) => term !== null),
);
const configKeys = computed(() => {
  const properties = (props.strategy.config_schema as { properties?: Record<string, unknown> })
    .properties;
  return Object.keys(properties || {});
});
</script>

<template>
  <aside
    class="strategy-inspector"
    :data-strategy="strategy.strategy_id"
    :aria-label="t('pipelines.strategy_details', 'Strategy details')"
  >
    <header>
      <h3>{{ pipelineStrategyLabel(strategy, t) }}</h3>
      <code>{{ strategy.strategy_id }}</code>
    </header>

    <section aria-labelledby="strategy-overview-title">
      <h4 id="strategy-overview-title">{{ t("pipelines.strategy_overview", "Overview") }}</h4>
      <p class="description">{{ pipelineStrategyDescription(strategy, t) }}</p>
      <dl>
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
        <div v-if="effect" class="effect">
          <dt>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</dt>
          <dd class="with-help">
            <strong v-if="note">{{ termLabel(note, t) }}</strong>
            <span v-else>{{ termLabel(effect, t) }}</span>
            <UiTooltip
              :text="termDescription(effect, t)"
              :label="t('pipelines.explain_scholarly_effect', 'Explain this scholarly effect')"
            />
          </dd>
        </div>
      </dl>
    </section>

    <section aria-labelledby="strategy-used-by-title">
      <h4 id="strategy-used-by-title">{{ t("pipelines.strategy_used_by", "Used by") }}</h4>
      <p v-if="categories.length" class="workflows">
        {{ categories.map((term) => termLabel(term, t)).join(", ") }}
      </p>
      <p v-if="!usage.pipelines.length" class="empty">
        {{ t("pipelines.strategy_unused", "No current pipeline") }}
      </p>
      <ul v-else class="usage-list">
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
    </section>

    <details class="strategy-technical">
      <summary>{{ t("pipelines.strategy_technical", "Technical details") }}</summary>
      <dl>
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
  </aside>
</template>

<style scoped>
.strategy-inspector {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
@media (min-width: 961px) {
  .strategy-inspector {
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
.strategy-inspector h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  line-height: var(--lh-tight);
}
.strategy-inspector header code,
.strategy-technical code {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.strategy-inspector h4 {
  margin: 0 0 var(--space-2);
  color: var(--text-primary);
  font-size: 1rem;
}
.strategy-inspector section {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.description {
  margin: 0 0 var(--space-3);
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.strategy-inspector dl {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}
.strategy-inspector dt {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.strategy-inspector dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
  overflow-wrap: anywhere;
}
.strategy-inspector dd code + code {
  margin-left: var(--space-2);
}
.with-help {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
}
.workflows,
.empty,
.usage-meta {
  margin: 0 0 var(--space-2);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.usage-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.usage-list li {
  display: grid;
}
.link-button {
  justify-self: start;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
  text-align: left;
  text-decoration: underline;
  cursor: pointer;
}
.link-button:focus-visible,
.strategy-technical summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.strategy-technical summary {
  width: fit-content;
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: var(--fw-bold);
  cursor: pointer;
}
.strategy-technical dl {
  margin-top: var(--space-2);
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

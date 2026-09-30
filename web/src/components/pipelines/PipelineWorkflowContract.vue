<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { findTerm, purposeText, termDescription, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  pipeline: PipelineDefinition;
  purpose: PipelinePurpose | null;
  vocabulary: PipelineWorkflowVocabulary;
  assignment: PipelineAssignment | null;
  assigned: boolean;
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const category = computed(() =>
  props.purpose ? findTerm(props.vocabulary.categories, props.purpose.category) : null,
);
const guarantees = computed(() =>
  (props.purpose?.required_guarantees || [])
    .map((id) => findTerm(props.vocabulary.guarantees, id))
    .filter((term) => term !== null),
);
const assignmentText = computed(() => {
  const current = props.assignment;
  if (props.assigned)
    return t("pipelines.contract_assigned", "Assigned — DerridAI runs this version");
  if (!current) return t("pipelines.not_assigned", "Not assigned");
  return i18n.tf("pipelines.contract_other_assigned", "Not assigned — {pipeline} runs instead", {
    pipeline: `${current.pipeline_id}@${current.pipeline_version}`,
  });
});
</script>

<template>
  <section class="workflow-contract" aria-labelledby="pipeline-contract-title">
    <h4 id="pipeline-contract-title">
      {{ t("pipelines.contract_title", "What this pipeline does") }}
    </h4>
    <p v-if="!purpose" class="contract-unregistered">
      {{
        i18n.tf(
          "pipelines.contract_unregistered",
          "The purpose {purpose} is not a registered workflow, so DerridAI cannot run this pipeline.",
          { purpose: pipeline.purpose },
        )
      }}
    </p>
    <template v-else>
      <p class="contract-summary">{{ purposeText(purpose, "description", t) }}</p>
      <dl class="contract-grid">
        <div>
          <dt>{{ t("pipelines.used_for", "Used for") }}</dt>
          <dd>
            <strong v-if="category">{{ termLabel(category, t) }}</strong>
            <span class="contract-purpose">{{ purposeText(purpose, "label", t) }}</span>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.contract_used_by", "Used by") }}</dt>
          <dd>{{ purposeText(purpose, "consumer", t) }}</dd>
        </div>
        <div>
          <dt>{{ t("pipelines.contract_input", "Input") }}</dt>
          <dd>{{ purposeText(purpose, "input", t) }}</dd>
        </div>
        <div>
          <dt>{{ t("pipelines.contract_output", "Output") }}</dt>
          <dd>{{ purposeText(purpose, "output", t) }}</dd>
        </div>
        <div class="contract-wide">
          <dt>{{ t("pipelines.contract_authority", "What the output establishes") }}</dt>
          <dd>{{ purposeText(purpose, "authority", t) }}</dd>
        </div>
        <div v-if="guarantees.length" class="contract-wide">
          <dt>{{ t("pipelines.contract_guarantees", "Required guarantees") }}</dt>
          <dd>
            <ul class="guarantee-list">
              <li v-for="term in guarantees" :key="term.id">
                {{ termLabel(term, t) }}
                <UiTooltip
                  :text="termDescription(term, t)"
                  :label="t('pipelines.explain_guarantee', 'Explain this guarantee')"
                />
              </li>
            </ul>
          </dd>
        </div>
        <div class="contract-wide">
          <dt>{{ t("pipelines.assignment", "Assignment") }}</dt>
          <dd>
            {{ assignmentText }}
            <code class="contract-version">{{ pipeline.pipeline_id }}@{{ pipeline.version }}</code>
          </dd>
        </div>
      </dl>
    </template>
  </section>
</template>

<style scoped>
.workflow-contract {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.workflow-contract h4 {
  margin: 0;
  font-size: 0.82rem;
}
.contract-summary,
.contract-unregistered {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.5;
}
.contract-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  margin: 0;
}
.contract-grid > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.contract-wide {
  grid-column: 1 / -1;
}
.contract-grid dt {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.contract-grid dd {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.contract-grid dd strong {
  margin-right: 6px;
}
.contract-purpose {
  color: var(--muted);
}
.guarantee-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.guarantee-list li {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.contract-version {
  margin-left: 6px;
  color: var(--muted);
  font-size: 0.75rem;
}
@media (max-width: 680px) {
  .contract-grid {
    grid-template-columns: 1fr;
  }
}
</style>

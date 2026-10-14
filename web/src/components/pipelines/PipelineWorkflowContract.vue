<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed } from "vue";
import { findTerm, purposeText, termDescription, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  pipeline: PipelineDefinition;
  purpose: PipelinePurpose | null;
  vocabulary: PipelineWorkflowVocabulary;
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
      </dl>
    </template>
  </section>
</template>

<style scoped>
.workflow-contract {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.workflow-contract h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}
.contract-summary,
.contract-unregistered {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.contract-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3) var(--space-5, 20px);
  margin: var(--space-2) 0 0;
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
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.contract-grid dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
  overflow-wrap: anywhere;
}
.contract-grid dd strong {
  margin-right: var(--space-2);
}
.contract-purpose {
  color: var(--text-tertiary);
}
.guarantee-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}
.guarantee-list li {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
@media (max-width: 680px) {
  .contract-grid {
    grid-template-columns: 1fr;
  }
}
</style>

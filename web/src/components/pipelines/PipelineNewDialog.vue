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
import { computed, ref } from "vue";
import PipelineTypeChip from "./PipelineTypeChip.vue";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import { findTerm, purposeText, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type { PipelinePurpose, PipelineWorkflowVocabulary } from "../../types/pipelines";

const props = defineProps<{
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  /** Preselected workflow, for example the one the navigator is filtered to. */
  initial?: string;
  busy?: boolean;
}>();
const emit = defineEmits<{ close: []; create: [purposeId: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const chosen = ref(props.initial || "");

const groups = computed(() =>
  props.vocabulary.categories
    .map((category) => ({
      id: category.id,
      label: termLabel(category, t),
      purposes: props.purposes.filter((purpose) => purpose.category === category.id),
    }))
    .filter((group) => group.purposes.length),
);
const selected = computed(
  () => props.purposes.find((purpose) => purpose.purpose_id === chosen.value) ?? null,
);
const guarantees = computed(() =>
  (selected.value?.required_guarantees ?? []).map((id) => {
    const term = findTerm(props.vocabulary.guarantees, id);
    return term ? termLabel(term, t) : id;
  }),
);
</script>

<template>
  <UiDialog
    :title="t('pipelines.new_dialog_title', 'New pipeline')"
    :description="
      t(
        'pipelines.new_dialog_description',
        'A pipeline is built for one workflow. Choose which; you start with one stage and add the rest, and every stage’s inputs are checked as you go.',
      )
    "
    :close-label="t('common.close', 'Close')"
    size="large"
    @close="emit('close')"
  >
    <div class="new-pipeline">
      <fieldset v-for="group in groups" :key="group.id" class="group">
        <legend>{{ group.label }}</legend>
        <label
          v-for="purpose in group.purposes"
          :key="purpose.purpose_id"
          class="choice"
          :data-selected="chosen === purpose.purpose_id"
        >
          <input
            v-model="chosen"
            type="radio"
            name="new-pipeline-workflow"
            :value="purpose.purpose_id"
          />
          <span class="choice-copy">
            <strong>{{ purposeText(purpose, "label", t) }}</strong>
            <span>{{ purposeText(purpose, "description", t) }}</span>
          </span>
        </label>
      </fieldset>

      <section v-if="selected" class="contract" aria-live="polite">
        <h4>{{ t("pipelines.new_dialog_contract", "What this workflow provides and expects") }}</h4>
        <dl>
          <div>
            <dt>{{ t("pipelines.new_dialog_supplies", "Supplies to every run") }}</dt>
            <dd class="inline">
              <template v-if="selected.run_inputs?.length">
                <span v-for="input in selected.run_inputs" :key="input.name" class="supplied">
                  <code>{{ input.name }}</code>
                  <PipelineTypeChip :type="input.data_type" />
                </span>
              </template>
              <span v-else>{{ purposeText(selected, "input", t) }}</span>
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.new_dialog_input_meaning", "What the input is") }}</dt>
            <dd>{{ purposeText(selected, "input", t) }}</dd>
          </div>
          <div>
            <dt>{{ t("pipelines.new_dialog_returns", "Must return") }}</dt>
            <dd class="inline">
              <PipelineTypeChip :type="selected.output_type" />
              <span>{{ purposeText(selected, "output", t) }}</span>
            </dd>
          </div>
          <div v-if="guarantees.length">
            <dt>{{ t("pipelines.new_dialog_guarantees", "Always enforced") }}</dt>
            <dd>{{ guarantees.join(" · ") }}</dd>
          </div>
        </dl>
      </section>
    </div>
    <template #footer>
      <UiButton :label="t('common.cancel', 'Cancel')" :disabled="busy" @click="emit('close')" />
      <UiButton
        variant="primary"
        :label="
          busy
            ? t('pipelines.new_dialog_starting', 'Starting…')
            : t('pipelines.new_dialog_start', 'Start building')
        "
        :disabled="!selected || busy"
        :disabled-reason="t('pipelines.new_dialog_choose', 'Choose a workflow first.')"
        @click="selected && emit('create', selected.purpose_id)"
      />
    </template>
  </UiDialog>
</template>

<style scoped>
.new-pipeline {
  display: grid;
  gap: var(--space-3);
}
.group {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  border: 0;
}
.group legend {
  padding: 0;
  margin-bottom: var(--space-1);
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.choice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  cursor: pointer;
}
.choice[data-selected="true"] {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.choice:focus-within {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.choice-copy {
  display: grid;
  gap: 2px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.choice-copy strong {
  color: var(--text-primary);
  font-size: 0.875rem;
}
.contract {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.contract h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.9375rem;
}
.contract dl {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}
.contract dt {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.contract dd {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.supplied {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
</style>

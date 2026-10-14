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
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";

defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const organization = [
  ["studio_pipelines", "Pipelines", "help_org_pipelines"],
  ["studio_strategies", "Strategies", "help_org_strategies"],
  ["studio_executions", "Executions", "help_org_executions"],
  ["studio_operations", "Operations", "help_org_operations"],
] as const;
const organizationDefaults: Record<string, string> = {
  help_org_pipelines:
    "Browse saved pipelines and their versions, read what each one guarantees, and clone a version to edit it.",
  help_org_strategies:
    "Every operation a stage can run, with its computation, inputs and outputs, and scholarly effect.",
  help_org_executions:
    "An audit history of what actually ran, including stage timings, fallbacks, and models.",
  help_org_operations:
    "Operational health, side-by-side comparison of two pipelines, and fixed benchmark cases.",
};
const concepts = [
  [
    "term_pipeline",
    "Pipeline",
    "term_pipeline_help",
    "A saved, versioned sequence of steps that determines how DerridAI finds candidate passages, orders them, checks provenance, prepares evidence, and, when applicable, asks a language model to produce or evaluate an answer.",
  ],
  [
    "used_for",
    "Used for",
    "term_used_for_help",
    "What the whole pipeline is for—Research, Evidence, Search, Metadata, Memory or Corpus processing—and which part of DerridAI runs it. A version keeps its purpose for life.",
  ],
  [
    "term_purpose",
    "Purpose",
    "term_purpose_help",
    "The precise system use a pipeline version serves within its workflow, for example reviewer evidence suggestion.",
  ],
  [
    "term_stage",
    "Stage",
    "term_stage_help",
    "One step in the recipe, such as retrieving passages, reranking them, checking provenance, or generating an answer.",
  ],
  [
    "term_strategy",
    "Strategy",
    "term_strategy_help",
    "The approved operation a stage performs. In technical terms, it is a registered server-side implementation with a known input, output, and configuration schema.",
  ],
  [
    "scholarly_effect",
    "Scholarly effect",
    "term_scholarly_effect_help",
    "What a stage establishes about evidence, support or provenance. Retrieval, reranking and diversity only order candidates; they never make a passage evidence.",
  ],
  [
    "term_edge",
    "Connection / edge",
    "term_edge_help",
    "A direction from one stage to another. Normal edges describe the usual path; fallback edges describe what to do when a stage is empty, unavailable, timed out, or fails.",
  ],
  [
    "term_assignment",
    "Assignment",
    "term_assignment_help",
    "The version DerridAI uses by default for a feature. Saving a new version does not change the assignment; activation is a separate, explicit step.",
  ],
  [
    "term_trace",
    "Execution trace",
    "term_trace_help",
    "An audit record of what actually ran: the exact version, stage path, fallbacks, models, candidate counts, and timings. This lets you distinguish the intended recipe from the runtime history.",
  ],
] as const;
</script>

<template>
  <UiDialog
    :open="open"
    :title="t('pipelines.help_title', 'Pipeline Studio help')"
    :description="
      t(
        'pipelines.plain_intro',
        'It is a saved sequence of steps that determines how DerridAI finds candidate passages, orders them, checks provenance, prepares evidence, and—when applicable—asks a language model to produce or evaluate an answer.',
      )
    "
    :close-label="t('common.close', 'Close')"
    size="large"
    @close="emit('close')"
  >
    <div class="pipeline-help">
      <section aria-labelledby="pipeline-help-organization">
        <h3 id="pipeline-help-organization">
          {{ t("pipelines.help_organization_title", "How Pipeline Studio is organized") }}
        </h3>
        <dl>
          <template v-for="[label, fallback, help] in organization" :key="label">
            <dt>{{ t(`pipelines.${label}`, fallback) }}</dt>
            <dd>{{ t(`pipelines.${help}`, organizationDefaults[help]) }}</dd>
          </template>
        </dl>
      </section>

      <section aria-labelledby="pipeline-help-concepts">
        <h3 id="pipeline-help-concepts">
          {{ t("pipelines.help_concepts_title", "Core concepts") }}
        </h3>
        <dl>
          <template v-for="[label, fallback, help, helpFallback] in concepts" :key="label">
            <dt>{{ t(`pipelines.${label}`, fallback) }}</dt>
            <dd>{{ t(`pipelines.${help}`, helpFallback) }}</dd>
          </template>
        </dl>
      </section>

      <section aria-labelledby="pipeline-help-lifecycle">
        <h3 id="pipeline-help-lifecycle">
          {{ t("pipelines.help_lifecycle_title", "Pipeline lifecycle") }}
        </h3>
        <p>
          {{
            t(
              "pipelines.help_lifecycle_body",
              "Versions are immutable. Clone a version to edit it, validate the draft on the server, and save it as a new version. Saving does not activate it: assigning a version to its feature is a separate, explicit step, and only active, executable versions can be assigned.",
            )
          }}
        </p>
      </section>

      <section aria-labelledby="pipeline-help-graphs">
        <h3 id="pipeline-help-graphs">
          {{ t("pipelines.help_graphs_title", "Reading pipeline graphs") }}
        </h3>
        <p>
          {{
            t(
              "pipelines.help_graphs_body",
              "Each node is a stage and each arrow is a connection. Solid arrows are the normal path; dashed arrows are fallbacks taken when a stage is empty, unavailable, timed out, or fails. Select a node to inspect its strategy and scholarly effect; in an execution, nodes also show what actually ran.",
            )
          }}
        </p>
      </section>
    </div>
    <template #footer>
      <UiButton :label="t('common.close', 'Close')" @click="emit('close')" />
    </template>
  </UiDialog>
</template>

<style scoped>
.pipeline-help {
  display: grid;
  gap: var(--space-5);
}
.pipeline-help h3 {
  margin: 0 0 var(--space-2);
  color: var(--text-primary);
  font-size: 1rem;
}
.pipeline-help p,
.pipeline-help dd {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.pipeline-help dl {
  display: grid;
  gap: var(--space-2) var(--space-4);
  grid-template-columns: minmax(120px, 200px) minmax(0, 1fr);
  margin: 0;
}
.pipeline-help dt {
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
}
@media (max-width: 680px) {
  .pipeline-help dl {
    grid-template-columns: 1fr;
  }
  .pipeline-help dd {
    margin-bottom: var(--space-2);
  }
}
</style>

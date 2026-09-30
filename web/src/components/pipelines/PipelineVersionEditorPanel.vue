<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import PipelineDefinitionEditor from "./PipelineDefinitionEditor.vue";
import { findTerm, purposeText, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineValidationResponse,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
const props = defineProps<{
  strategies: PipelineStrategy[];
  purpose: PipelinePurpose | null;
  vocabulary: PipelineWorkflowVocabulary;
  validation: PipelineValidationResponse | null;
  saving: boolean;
}>();

const model = defineModel<PipelineDefinition>({ required: true });
const emit = defineEmits<{
  cancel: [];
  validate: [];
  save: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const category = computed(() =>
  props.purpose ? findTerm(props.vocabulary.categories, props.purpose.category) : null,
);
const purposeLabel = computed(() =>
  props.purpose ? purposeText(props.purpose, "label", t) : model.value.purpose,
);
</script>

<template>
  <section class="editor-card" aria-labelledby="pipeline-editor-title">
    <header class="editor-heading">
      <div>
        <div class="detail-kicker">{{ t("pipelines.new_version", "New pipeline version") }}</div>
        <h3 id="pipeline-editor-title">
          {{ t("pipelines.configure_clone", "Configure cloned pipeline") }}
        </h3>
        <p class="editor-subtitle">
          {{
            t(
              "pipelines.configure_clone_help",
              "Edit the copy below. Validation checks whether the graph is internally coherent and whether the current runtime knows how to execute it. Saving does not activate it.",
            )
          }}
        </p>
      </div>
      <button class="btn" type="button" @click="emit('cancel')">
        {{ t("common.cancel", "Cancel") }}
      </button>
    </header>

    <section class="editor-purpose" aria-labelledby="pipeline-editor-purpose">
      <p id="pipeline-editor-purpose" class="purpose-line">
        <span class="purpose-label">{{ t("pipelines.used_for", "Used for") }}</span>
        <strong v-if="category">{{ termLabel(category, t) }}</strong>
        <span v-if="category" aria-hidden="true">·</span>
        <strong>{{ purposeLabel }}</strong>
      </p>
      <p class="purpose-help">
        {{
          i18n.tf(
            "pipelines.editor_purpose_fixed",
            "This new version remains a {purpose} pipeline. To create a pipeline for another workflow, begin from a pipeline for that workflow instead.",
            { purpose: purposeLabel },
          )
        }}
      </p>
    </section>

    <PipelineDefinitionEditor v-model="model" :strategies="strategies" :purpose="purpose" />

    <div
      v-if="validation"
      class="validation-result"
      :data-valid="validation.validation.valid"
      role="status"
    >
      <strong>
        {{
          validation.validation.valid
            ? t("pipelines.graph_valid", "Graph is valid")
            : t("pipelines.graph_invalid", "Graph needs changes")
        }}
      </strong>
      <span v-if="!validation.runtime_supported">
        {{
          validation.runtime_error ||
          t(
            "pipelines.not_runtime_supported",
            "This graph is not executable by the current adapter.",
          )
        }}
      </span>
      <ul v-if="validation.validation.issues.length">
        <li
          v-for="issue in validation.validation.issues"
          :key="`${issue.code}:${issue.stage_id || ''}`"
        >
          {{ issue.message }}
        </li>
      </ul>
    </div>

    <footer class="editor-actions">
      <span class="action-with-help">
        <button class="btn" type="button" :disabled="saving" @click="emit('validate')">
          {{ t("pipelines.validate", "Validate") }}
        </button>
        <UiTooltip
          :text="
            t(
              'pipelines.validate_help',
              'Validation is a dry check. It does not run the pipeline against your corpus and does not save anything. It checks graph structure, registered strategy settings, and current runtime support.',
            )
          "
        />
      </span>
      <span class="action-with-help">
        <button class="btn primary" type="button" :disabled="saving" @click="emit('save')">
          <AppIcon name="check" />
          {{
            saving ? t("pipelines.saving", "Saving…") : t("pipelines.save_version", "Save version")
          }}
        </button>
        <UiTooltip
          :text="
            t(
              'pipelines.save_version_help',
              'Saving creates a new immutable pipeline version for auditability. It does not replace the source version and does not make the new version the system default.',
            )
          "
        />
      </span>
    </footer>
  </section>
</template>

<style scoped>
.editor-purpose {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-left: 3px solid currentColor;
  border-radius: 10px;
  background: var(--soft);
}
.purpose-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
  margin: 0;
  font-size: 0.86rem;
}
.purpose-label {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.purpose-help {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
}
.editor-card {
  display: grid;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.editor-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.detail-kicker {
  margin-bottom: 3px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.editor-heading h3 {
  margin: 0;
  font-size: 1rem;
}
.editor-subtitle {
  max-width: 760px;
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
}
.validation-result {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
  font-size: 0.78rem;
}
.validation-result > span,
.validation-result li {
  color: var(--muted);
}
.validation-result ul {
  margin: 3px 0 0;
  padding-left: 18px;
}
.editor-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
}
.action-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.editor-actions :deep(svg) {
  width: 15px;
  height: 15px;
}
@media (max-width: 680px) {
  .editor-heading {
    display: grid;
  }
  .editor-actions {
    justify-content: stretch;
  }
  .editor-actions .btn {
    flex: 1;
  }
}
</style>

<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import PipelineDefinitionEditor from "./PipelineDefinitionEditor.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelineStrategy,
  PipelineValidationResponse,
} from "../../types/pipelines";

defineProps<{
  strategies: PipelineStrategy[];
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
</script>

<template>
  <section class="editor-card" aria-labelledby="pipeline-editor-title">
    <header class="editor-heading">
      <div>
        <div class="detail-kicker">{{ t("pipelines.new_version", "New pipeline version") }}</div>
        <h3 id="pipeline-editor-title">
          {{ t("pipelines.configure_clone", "Configure cloned pipeline") }}
        </h3>
      </div>
      <button class="btn" type="button" @click="emit('cancel')">
        {{ t("common.cancel", "Cancel") }}
      </button>
    </header>

    <PipelineDefinitionEditor v-model="model" :strategies="strategies" />

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
      <button class="btn" type="button" :disabled="saving" @click="emit('validate')">
        {{ t("pipelines.validate", "Validate") }}
      </button>
      <button class="btn primary" type="button" :disabled="saving" @click="emit('save')">
        <AppIcon name="check" />
        {{ saving ? t("pipelines.saving", "Saving…") : t("pipelines.save_version", "Save version") }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
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

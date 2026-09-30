<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { pipelineDefinitionStatusLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineDefinition } from "../../types/pipelines";

const props = defineProps<{ modelValue: PipelineDefinition }>();
const emit = defineEmits<{
  update: [key: "pipeline_id" | "version" | "name" | "status" | "notes", value: unknown];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const incomplete = computed(
  () =>
    !props.modelValue.pipeline_id.trim() ||
    !props.modelValue.name.trim() ||
    !(Number(props.modelValue.version) >= 1),
);
const open = ref(incomplete.value);
watch(incomplete, (value) => {
  if (value) open.value = true;
});
</script>

<template>
  <details
    class="version-details"
    :open="open"
    @toggle="open = ($event.target as HTMLDetailsElement).open"
  >
    <summary>
      <span class="summary-title">{{ t("pipelines.version_details", "Version details") }}</span>
      <span class="summary-value">
        {{ modelValue.name || t("pipelines.unnamed_pipeline", "Unnamed pipeline") }} ·
        <code>{{ modelValue.pipeline_id || "—" }}@{{ modelValue.version }}</code> ·
        {{ pipelineDefinitionStatusLabel(modelValue.status, t) }}
      </span>
    </summary>
    <div class="version-fields">
      <p class="identity-summary">
        {{
          t(
            "pipelines.identity_summary",
            "Pipeline ID stays stable across versions. Every saved version is immutable so past runs can resolve the exact configuration.",
          )
        }}
      </p>
      <div class="identity-grid">
        <label>
          <span class="label-with-help">
            {{ t("pipelines.pipeline_id", "Pipeline ID") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.pipeline_id_help',
                  'A stable technical name used by DerridAI and its audit records. Versions that belong to the same pipeline share this ID. It is not the human-readable display name.',
                )
              "
            />
          </span>
          <input
            class="control"
            :value="modelValue.pipeline_id"
            autocomplete="off"
            @input="emit('update', 'pipeline_id', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label>
          <span class="label-with-help">
            {{ t("pipelines.version", "Version") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.version_help',
                  'An immutable revision number. A saved ID and version pair can never be overwritten, so past Research runs can always point to the exact configuration they used.',
                )
              "
            />
          </span>
          <input
            class="control"
            type="number"
            min="1"
            step="1"
            :value="modelValue.version"
            @input="
              emit(
                'update',
                'version',
                Math.max(1, Number(($event.target as HTMLInputElement).value) || 1),
              )
            "
          />
        </label>
        <label class="identity-name">
          <span class="label-with-help">
            {{ t("pipelines.name", "Name") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.name_help',
                  'A human-readable title for administrators and researchers. Changing the name does not change the technical pipeline ID.',
                )
              "
            />
          </span>
          <input
            class="control"
            :value="modelValue.name"
            @input="emit('update', 'name', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label>
          <span class="label-with-help">
            {{ t("pipelines.status", "Status") }}
            <UiTooltip
              :text="
                t(
                  'pipelines.status_help',
                  'Draft means editable configuration that cannot become the system assignment yet. Active means eligible to be assigned. Disabled keeps the version for history but prevents new selection.',
                )
              "
            />
          </span>
          <select
            class="control"
            :value="modelValue.status"
            @change="emit('update', 'status', ($event.target as HTMLSelectElement).value)"
          >
            <option value="draft">{{ t("pipelines.status_draft", "Draft") }}</option>
            <option value="active">{{ t("pipelines.status_active", "Active") }}</option>
            <option value="disabled">{{ t("pipelines.status_disabled", "Disabled") }}</option>
          </select>
          <small class="field-help">{{
            t(
              "pipelines.status_summary",
              "Draft is editable; Active can be assigned; Disabled is retained for history but cannot be newly selected.",
            )
          }}</small>
        </label>
      </div>
      <label class="notes-field">
        <span class="label-with-help">
          {{ t("pipelines.notes", "Notes") }}
          <UiTooltip
            :text="
              t(
                'pipelines.notes_help',
                'Use notes to record the scholarly or technical reason for this version—for example, why retrieval depth changed or why a fallback was added.',
              )
            "
          />
        </span>
        <textarea
          class="control"
          rows="3"
          :value="modelValue.notes || ''"
          @input="emit('update', 'notes', ($event.target as HTMLTextAreaElement).value || null)"
        />
      </label>
    </div>
  </details>
</template>

<style scoped>
.version-details {
  padding: var(--space-3) 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.version-details summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  align-items: baseline;
  cursor: pointer;
}
.version-details summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.summary-title {
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: var(--fw-bold);
}
.summary-value {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.version-fields {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-3);
}
.identity-summary {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.field-help {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.identity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}
.identity-grid label,
.notes-field {
  display: grid;
  gap: var(--space-1);
}
.identity-grid label > span,
.notes-field > span {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.identity-name {
  grid-column: span 2;
}
.notes-field textarea {
  min-height: 76px;
  resize: vertical;
}
@media (max-width: 680px) {
  .identity-grid {
    grid-template-columns: 1fr;
  }
  .identity-name {
    grid-column: auto;
  }
}
</style>

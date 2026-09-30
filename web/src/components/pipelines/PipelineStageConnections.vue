<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import UiTagPicker from "../ui/UiTagPicker.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import type { PipelineStage } from "../../types/pipelines";

type FallbackKey = "on_empty" | "on_unavailable" | "on_timeout" | "on_error";

const props = defineProps<{
  stage: PipelineStage;
  stages: PipelineStage[];
}>();

const emit = defineEmits<{
  toggleNext: [targetId: string, checked: boolean];
  updateFallback: [key: FallbackKey, target: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const fallbackOptions: Array<{ key: FallbackKey; label: () => string }> = [
  { key: "on_empty", label: () => t("pipelines.on_empty", "On empty") },
  { key: "on_unavailable", label: () => t("pipelines.on_unavailable", "On unavailable") },
  { key: "on_timeout", label: () => t("pipelines.on_timeout", "On timeout") },
  { key: "on_error", label: () => t("pipelines.on_error", "On error") },
];

function targets() {
  return props.stages.filter((item) => item.id !== props.stage.id);
}

function updateNext(ids: string[]) {
  const before = new Set(props.stage.next);
  const after = new Set(ids);
  for (const id of after) if (!before.has(id)) emit("toggleNext", id, true);
  for (const id of before) if (!after.has(id)) emit("toggleNext", id, false);
}
</script>

<template>
  <section class="edge-editor" aria-labelledby="stage-connections-heading">
    <h5 id="stage-connections-heading" class="label-with-help">
      {{ t("pipelines.connections", "Connections") }}
      <UiTooltip
        :text="
          t(
            'pipelines.connections_help',
            'Connections say what should happen after this stage. “Next stages” are the normal route. Fallbacks are alternate routes used only when a specific problem occurs.',
          )
        "
      />
    </h5>
    <div class="edge-group">
      <p class="edge-label label-with-help">
        {{ t("pipelines.normal_flow", "Normal flow") }}
        <UiTooltip
          :text="
            t(
              'pipelines.next_stages_help',
              'These are the stages DerridAI should run next when this step completes normally. In graph terminology, each checked item creates a directed edge.',
            )
          "
        />
      </p>
      <UiTagPicker
        :model-value="stage.next"
        :options="targets().map((target) => target.id)"
        :label="t('pipelines.next_stages', 'Next stages')"
        :remove-label="t('pipelines.remove_next_stage', 'Remove {value} from next stages')"
        :placeholder="t('pipelines.add_next_stage', 'Add a next stage…')"
        :disabled="stages.length <= 1"
        @update:model-value="updateNext"
      />
      <small v-if="stages.length <= 1" class="edge-note">
        {{ t("pipelines.no_other_stages", "Add another stage to create an edge.") }}
      </small>
    </div>

    <div class="edge-group">
      <p class="edge-label">{{ t("pipelines.fallback_flow", "Fallback flow") }}</p>
      <label v-for="fallback in fallbackOptions" :key="fallback.key" class="fallback-row">
        <span class="label-with-help">
          {{ fallback.label() }}
          <UiTooltip
            :text="
              fallback.key === 'on_empty'
                ? t(
                    'pipelines.on_empty_help',
                    'Use this alternate route when the stage completes but produces no usable items.',
                  )
                : fallback.key === 'on_unavailable'
                  ? t(
                      'pipelines.on_unavailable_help',
                      'Use this alternate route when the required model, service, dependency, or capability is not available.',
                    )
                  : fallback.key === 'on_timeout'
                    ? t(
                        'pipelines.on_timeout_help',
                        'Use this alternate route when the stage takes longer than its allowed time.',
                      )
                    : t(
                        'pipelines.on_error_help',
                        'Use this alternate route when the stage fails for another runtime error.',
                      )
            "
          />
        </span>
        <select
          class="control"
          :value="stage[fallback.key] || ''"
          @change="emit('updateFallback', fallback.key, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">{{ t("pipelines.no_fallback", "No fallback") }}</option>
          <option v-for="target in targets()" :key="target.id" :value="target.id">
            {{ target.id }}
          </option>
        </select>
      </label>
    </div>
  </section>
</template>

<style scoped>
.edge-editor {
  display: grid;
  gap: var(--space-3);
}
.edge-editor h5 {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.9375rem;
}
.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.edge-group {
  display: grid;
  gap: var(--space-2);
}
.edge-label {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.edge-note {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.fallback-row {
  display: grid;
  grid-template-columns: minmax(6.5rem, 0.8fr) minmax(0, 1.2fr);
  align-items: center;
  gap: var(--space-2);
  color: var(--text-secondary);
  font-size: 0.875rem;
}
.fallback-row .control {
  width: 100%;
  min-height: var(--control-height-small);
}
</style>

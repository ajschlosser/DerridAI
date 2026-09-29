<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
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
</script>

<template>
  <fieldset class="edge-editor">
    <legend>{{ t("pipelines.connections", "Connections") }}</legend>
    <div class="edge-grid">
      <div class="next-targets">
        <span class="edge-label">{{ t("pipelines.next_stages", "Next stages") }}</span>
        <div class="edge-target-list">
          <label v-for="target in targets()" :key="target.id">
            <input
              type="checkbox"
              :checked="stage.next.includes(target.id)"
              @change="emit('toggleNext', target.id, ($event.target as HTMLInputElement).checked)"
            />
            <code>{{ target.id }}</code>
          </label>
          <small v-if="stages.length <= 1">
            {{ t("pipelines.no_other_stages", "Add another stage to create an edge.") }}
          </small>
        </div>
      </div>

      <div class="fallback-grid">
        <label v-for="fallback in fallbackOptions" :key="fallback.key">
          <span>{{ fallback.label() }}</span>
          <select
            class="control"
            :value="stage[fallback.key] || ''"
            @change="
              emit(
                'updateFallback',
                fallback.key,
                ($event.target as HTMLSelectElement).value,
              )
            "
          >
            <option value="">{{ t("pipelines.no_fallback", "No fallback") }}</option>
            <option v-for="target in targets()" :key="target.id" :value="target.id">
              {{ target.id }}
            </option>
          </select>
        </label>
      </div>
    </div>
  </fieldset>
</template>

<style scoped>
.edge-editor {
  margin: 0;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
}
.edge-editor legend {
  padding: 0 5px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
}
.edge-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 1fr);
  gap: 12px;
}
.next-targets {
  display: grid;
  align-content: start;
  gap: 6px;
}
.edge-label,
.fallback-grid label > span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.edge-target-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.edge-target-list label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 36px;
  padding: 5px 7px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  font-size: 0.75rem;
}
.edge-target-list code {
  overflow-wrap: anywhere;
}
.edge-target-list small {
  color: var(--muted);
  font-size: 0.75rem;
}
.fallback-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.fallback-grid label {
  display: grid;
  gap: 5px;
}
@media (max-width: 860px) {
  .edge-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 680px) {
  .fallback-grid {
    grid-template-columns: 1fr;
  }
}
</style>

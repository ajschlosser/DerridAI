<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import {
  pipelineEdgeKindLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineDefinition, PipelineStage, PipelineStrategy } from "../../types/pipelines";

const props = defineProps<{
  pipeline: PipelineDefinition;
  strategies: PipelineStrategy[];
}>();

const i18n = useI18nStore();
const strategyMap = computed(
  () => new Map(props.strategies.map((strategy) => [strategy.strategy_id, strategy])),
);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function strategy(stage: PipelineStage) {
  return strategyMap.value.get(stage.strategy);
}
function outgoing(stage: PipelineStage) {
  const values = [
    ...(stage.next || []).map((target) => ({ kind: "next", target })),
    ...(stage.on_empty ? [{ kind: "empty", target: stage.on_empty }] : []),
    ...(stage.on_unavailable ? [{ kind: "unavailable", target: stage.on_unavailable }] : []),
    ...(stage.on_timeout ? [{ kind: "timeout", target: stage.on_timeout }] : []),
    ...(stage.on_error ? [{ kind: "error", target: stage.on_error }] : []),
  ];
  return values;
}
function compactConfig(config: Record<string, unknown>) {
  const entries = Object.entries(config || {});
  if (!entries.length) return "";
  return entries
    .slice(0, 4)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(" · ");
}
</script>

<template>
  <ol class="pipeline-stage-list" :aria-label="t('pipelines.stages', 'Pipeline stages')">
    <li v-for="(stage, index) in pipeline.stages" :key="stage.id" class="stage-card">
      <div class="stage-index" aria-hidden="true">{{ index + 1 }}</div>
      <div class="stage-main">
        <div class="stage-title-row">
          <div>
            <strong>{{ strategy(stage) ? pipelineStrategyLabel(strategy(stage), t) : stage.strategy }}</strong>
            <code>{{ stage.id }}</code>
          </div>
          <div class="stage-badges">
            <span class="badge">{{ pipelineStageFamilyLabel(strategy(stage)?.family, t) }}</span>
            <span v-if="strategy(stage)?.invokes_llm" class="badge">
              <AppIcon name="spark" />
              {{ t("pipelines.llm", "LLM") }}
            </span>
            <span v-else class="badge">{{ t("pipelines.deterministic", "Deterministic") }}</span>
          </div>
        </div>
        <p v-if="strategy(stage)" class="stage-description">
          {{ pipelineStrategyDescription(strategy(stage), t) }}
        </p>
        <p v-if="compactConfig(stage.config)" class="stage-config">
          {{ compactConfig(stage.config) }}
        </p>
        <div v-if="outgoing(stage).length" class="stage-edges">
          <span v-for="edge in outgoing(stage)" :key="`${edge.kind}:${edge.target}`">
            {{ pipelineEdgeKindLabel(edge.kind, t) }}
            <code>{{ edge.target }}</code>
          </span>
        </div>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.pipeline-stage-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.stage-card {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.stage-index {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.78rem;
  font-weight: 800;
}
.stage-main {
  min-width: 0;
}
.stage-title-row {
  display: flex;
  gap: 12px;
  align-items: start;
  justify-content: space-between;
}
.stage-title-row strong {
  display: block;
  font-size: 0.9rem;
}
.stage-title-row code,
.stage-edges code {
  color: var(--muted);
  font-size: 0.76rem;
}
.stage-badges,
.stage-edges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.badge {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  padding: 2px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 700;
}
.badge :deep(svg) {
  width: 11px;
  height: 11px;
}
.stage-description,
.stage-config {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.45;
}
.stage-config {
  font-family: var(--font-mono, ui-monospace, monospace);
}
.stage-edges {
  margin-top: 8px;
  font-size: 0.75rem;
}
.stage-edges span {
  padding: 3px 6px;
  border-radius: 7px;
  background: var(--soft);
}
@media (max-width: 640px) {
  .stage-title-row {
    display: grid;
  }
}
</style>

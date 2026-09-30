<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import { pipelineStrategyLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineStage, PipelineStrategy } from "../../types/pipelines";

const props = defineProps<{
  stages: PipelineStage[];
  strategies: PipelineStrategy[];
  selectedIndex: number;
  entryStageIds: string[];
  canAdd: boolean;
}>();
const emit = defineEmits<{
  select: [index: number];
  add: [];
  move: [index: number, direction: -1 | 1];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

function strategyName(stage: PipelineStage) {
  const strategy = props.strategies.find((item) => item.strategy_id === stage.strategy);
  return strategy ? pipelineStrategyLabel(strategy, t) : stage.strategy;
}
function menuItems(index: number): UiMenuItem[] {
  return [
    {
      id: "up",
      label: t("pipelines.move_stage_up", "Move stage up"),
      reason:
        index === 0 ? t("pipelines.move_first_reason", "This is the first stage.") : undefined,
    },
    {
      id: "down",
      label: t("pipelines.move_stage_down", "Move stage down"),
      reason:
        index === props.stages.length - 1
          ? t("pipelines.move_last_reason", "This is the last stage.")
          : undefined,
    },
  ];
}
</script>

<template>
  <section class="stage-navigator" aria-labelledby="stage-navigator-title">
    <header>
      <h4 id="stage-navigator-title">{{ t("pipelines.stage_list_title", "Stages") }}</h4>
      <UiButton
        icon="plus"
        :label="t('pipelines.add_stage', 'Add stage')"
        size="small"
        :disabled="!canAdd"
        @click="emit('add')"
      />
    </header>
    <p class="order-note">
      {{
        t(
          "pipelines.stage_order_note",
          "Connections, not list order, define how execution flows. This list is for selecting and reading stages.",
        )
      }}
    </p>
    <ol>
      <li v-for="(stage, index) in stages" :key="`${stage.id}:${index}`">
        <button
          type="button"
          class="stage-row"
          :class="{ selected: index === selectedIndex }"
          :aria-current="index === selectedIndex ? 'true' : undefined"
          @click="emit('select', index)"
        >
          <span class="row-number" aria-hidden="true">{{ index + 1 }}</span>
          <span class="row-main">
            <strong>{{ stage.id || t("pipelines.unnamed_stage", "Unnamed stage") }}</strong>
            <small>
              {{ strategyName(stage) }}
              <template v-if="entryStageIds.includes(stage.id)">
                · {{ t("pipelines.node_entry", "Entry") }}</template
              >
              <template v-if="!stage.enabled">
                · {{ t("pipelines.node_disabled", "Disabled") }}</template
              >
            </small>
          </span>
        </button>
        <UiMenu
          label="⋯"
          :aria-label="
            i18n.tf('pipelines.stage_actions_for', 'Actions for {stage}', { stage: stage.id })
          "
          :items="menuItems(index)"
          :caret="false"
          align="end"
          @select="emit('move', index, $event === 'up' ? -1 : 1)"
        />
      </li>
    </ol>
  </section>
</template>

<style scoped>
.stage-navigator {
  display: grid;
  gap: var(--space-2);
}
.stage-navigator header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.stage-navigator h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}
.order-note {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.stage-navigator ol {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  overflow: hidden;
}
.stage-navigator li {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
}
.stage-navigator li:last-child {
  border-bottom: 0;
}
.stage-row {
  display: flex;
  flex: 1;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  min-height: 44px;
  padding: var(--space-2) var(--space-3);
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.stage-row:hover,
.stage-row.selected {
  background: var(--surface-selected);
}
.stage-row:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -2px;
}
.row-number {
  flex: 0 0 auto;
  min-width: 1.5em;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}
.row-main {
  display: grid;
  min-width: 0;
}
.row-main strong {
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.row-main small {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.stage-row.selected .row-main strong {
  color: var(--accent-fg);
}
.stage-navigator li :deep(.ui-menu) {
  padding-right: var(--space-2);
}
.stage-navigator li :deep(.ui-menu-trigger) {
  min-height: var(--control-height-small);
  border-color: transparent;
  background: transparent;
}
</style>

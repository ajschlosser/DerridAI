<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { AutonomousPolicy } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import CorpusExecutionSettings from "../CorpusExecutionSettings.vue";
import CorpusHandsFreeSettings from "../CorpusHandsFreeSettings.vue";

const props = defineProps<{
  generation: Record<string, unknown>;
  stageLimits: Record<string, number>;
  stageTimeouts: Record<string, number>;
  maxConcurrentRequests: number;
  useProfileDefaults: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  "update:generation": [value: Record<string, unknown>];
  "update:stageLimits": [value: Record<string, number>];
  "update:stageTimeouts": [value: Record<string, number>];
  "update:maxConcurrentRequests": [value: number];
  "update:useProfileDefaults": [value: boolean];
}>();

const handsFree = defineModel<AutonomousPolicy>("handsFree", { required: true });
const i18n = useI18nStore();
</script>

<template>
  <section
    id="corpus-config-panel-advanced"
    class="advanced-configuration-workspace"
    role="tabpanel"
    aria-labelledby="corpus-config-tab-advanced"
  >
    <details class="setup-section setup-disclosure">
      <summary>
        <span>
          <b>{{ i18n.t("pdf_corpus.hands_free_title") }}</b>
          <small>{{
            handsFree.enabled
              ? i18n.t("pdf_corpus.hands_free_on")
              : i18n.t("pdf_corpus.hands_free_off")
          }}</small>
        </span>
      </summary>
      <div class="setup-disclosure-body">
        <CorpusHandsFreeSettings v-model="handsFree" :disabled="props.disabled" />
      </div>
    </details>

    <div class="setup-section execution-wrapper">
      <div class="setup-section-inline-head">
        <span>
          <b>{{ i18n.t("pdf_corpus.advanced_execution") }}</b>
          <small>{{ i18n.t("pdf_corpus.advanced_execution_help") }}</small>
        </span>
      </div>
      <CorpusExecutionSettings
        class="execution-config"
        :generation="props.generation"
        :stage-limits="props.stageLimits"
        :stage-timeouts="props.stageTimeouts"
        :max-concurrent-requests="props.maxConcurrentRequests"
        :use-profile-defaults="props.useProfileDefaults"
        :disabled="props.disabled"
        @update:generation="emit('update:generation', $event)"
        @update:stage-limits="emit('update:stageLimits', $event)"
        @update:stage-timeouts="emit('update:stageTimeouts', $event)"
        @update:max-concurrent-requests="emit('update:maxConcurrentRequests', $event)"
        @update:use-profile-defaults="emit('update:useProfileDefaults', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.advanced-configuration-workspace {
  display: grid;
}
.setup-disclosure {
  overflow: visible;
  border-top: 1px solid var(--border-subtle);
}
.setup-disclosure > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 54px;
  padding: var(--space-3) 0;
}
.setup-disclosure > summary::-webkit-details-marker {
  display: none;
}
.setup-disclosure > summary > span:last-child {
  display: grid;
  gap: 2px;
}
.setup-disclosure > summary b {
  font-size: 0.9375rem;
}
.setup-disclosure > summary small {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 500;
}
.setup-disclosure[open] > summary {
  border-bottom: 1px solid var(--border-subtle);
}
.setup-disclosure-body {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0 var(--space-5);
}
.execution-wrapper {
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-subtle);
}
.setup-section-inline-head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}
.setup-section-inline-head > span:last-child {
  display: grid;
  gap: 2px;
}
.setup-section-inline-head b {
  font-size: 0.9375rem;
}
.setup-section-inline-head small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.execution-wrapper > .execution-config {
  border: 0;
}
.execution-wrapper :deep(.execution-settings-shell) {
  border: 0;
}
@media (max-width: 620px) {
  .setup-disclosure-body,
  .execution-wrapper {
    padding: 13px;
  }
  .setup-disclosure > summary {
    padding: 11px 13px;
  }
}
</style>

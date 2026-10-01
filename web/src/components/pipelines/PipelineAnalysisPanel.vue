<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import PipelineComplexityView from "./PipelineComplexityView.vue";
import PipelineLatencyView from "./PipelineLatencyView.vue";
import UiTabs from "../ui/UiTabs.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAnalysis,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  analysis: PipelineAnalysis | null;
  loading?: boolean;
  error?: string;
  strategies: PipelineStrategy[];
  vocabulary?: PipelineWorkflowVocabulary;
  selectedStageId?: string;
}>();
const emit = defineEmits<{ selectStage: [id: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const tab = ref("latency");
const issues = computed(() => props.analysis?.validation.issues ?? []);
const errorCount = computed(() => issues.value.filter((issue) => issue.level === "error").length);
const tabs = computed(() => [
  {
    id: "checks",
    label: issues.value.length
      ? i18n.tf("pipelines.analysis_tab_checks_count", "Checks ({count})", {
          count: issues.value.length,
        })
      : t("pipelines.analysis_tab_checks", "Checks"),
  },
  { id: "latency", label: t("pipelines.analysis_tab_latency", "Latency") },
  { id: "complexity", label: t("pipelines.analysis_tab_complexity", "Complexity") },
]);
</script>

<template>
  <section class="analysis" aria-labelledby="pipeline-analysis-heading">
    <header>
      <h4 id="pipeline-analysis-heading">
        {{ t("pipelines.analysis_title", "How this pipeline performs") }}
      </h4>
      <span v-if="loading" class="busy" role="status">
        {{ t("pipelines.analysis_updating", "Updating…") }}
      </span>
    </header>
    <p v-if="error" class="problem" role="alert">
      {{
        i18n.tf("pipelines.analysis_failed", "The analysis could not be loaded: {message}", {
          message: error,
        })
      }}
    </p>
    <template v-if="analysis">
      <UiTabs
        v-model="tab"
        id-prefix="pipeline-analysis"
        :tablist-label="t('pipelines.analysis_tabs', 'Pipeline analysis')"
        :tabs="tabs"
      />
      <div
        id="pipeline-analysis-panel-checks"
        role="tabpanel"
        aria-labelledby="pipeline-analysis-tab-checks"
        :hidden="tab !== 'checks'"
      >
        <div v-if="tab === 'checks'" class="checks">
          <p v-if="!issues.length" class="all-clear" role="status">
            {{
              t(
                "pipelines.checks_none",
                "No problems found. Every stage input has a source of the right type.",
              )
            }}
          </p>
          <template v-else>
            <p class="checks-summary" role="status">
              {{
                errorCount
                  ? i18n.tf(
                      "pipelines.checks_errors",
                      "{count} must be fixed before this version can be saved.",
                      { count: errorCount },
                    )
                  : t(
                      "pipelines.checks_warnings_only",
                      "Nothing blocks saving; review the notes below.",
                    )
              }}
            </p>
            <ul class="check-list">
              <li
                v-for="(issue, index) in issues"
                :key="`${issue.code}:${issue.stage_id}:${index}`"
                :data-level="issue.level"
              >
                <span class="check-level">
                  {{
                    issue.level === "error"
                      ? t("pipelines.checks_must_fix", "Must fix")
                      : t("pipelines.checks_review", "Review")
                  }}
                </span>
                <button
                  v-if="issue.stage_id"
                  type="button"
                  class="check-stage"
                  @click="emit('selectStage', issue.stage_id)"
                >
                  {{ issue.stage_id }}
                </button>
                <span class="check-message">{{ issue.message }}</span>
              </li>
            </ul>
          </template>
        </div>
      </div>
      <div
        id="pipeline-analysis-panel-latency"
        role="tabpanel"
        aria-labelledby="pipeline-analysis-tab-latency"
        :hidden="tab !== 'latency'"
      >
        <PipelineLatencyView
          v-if="tab === 'latency'"
          :latency="analysis.latency"
          :strategies="strategies"
          :sample="analysis.sample"
          :selected-stage-id="selectedStageId"
          @select-stage="emit('selectStage', $event)"
        />
      </div>
      <div
        id="pipeline-analysis-panel-complexity"
        role="tabpanel"
        aria-labelledby="pipeline-analysis-tab-complexity"
        :hidden="tab !== 'complexity'"
      >
        <PipelineComplexityView
          v-if="tab === 'complexity'"
          :complexity="analysis.complexity"
          :latency="analysis.latency"
          :strategies="strategies"
          :vocabulary="vocabulary"
          :selected-stage-id="selectedStageId"
          @select-stage="emit('selectStage', $event)"
        />
      </div>
    </template>
    <p v-else-if="!error" class="busy" role="status">
      {{ t("pipelines.analysis_loading", "Analyzing the pipeline…") }}
    </p>
  </section>
</template>

<style scoped>
.analysis {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.analysis header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.analysis h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}
.checks {
  display: grid;
  gap: var(--space-2);
}
.all-clear,
.checks-summary {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}
.check-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.check-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.875rem;
}
.check-list li[data-level="error"] {
  border-color: var(--tone-danger-edge);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.check-level {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.check-stage {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 800;
  text-decoration: underline;
  cursor: pointer;
}
.check-stage:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.check-message {
  flex: 1 1 260px;
}
.busy {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.problem {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: 0.875rem;
}
</style>

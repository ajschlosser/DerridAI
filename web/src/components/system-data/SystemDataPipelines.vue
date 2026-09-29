<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import PipelineDefinitionEditor from "../pipelines/PipelineDefinitionEditor.vue";
import PipelineRunTracePanel from "../pipelines/PipelineRunTracePanel.vue";
import PipelineStageList from "../pipelines/PipelineStageList.vue";
import { pipelinesApi } from "../../api/pipelines";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineRunTrace,
  PipelineValidationResponse,
} from "../../types/pipelines";

const i18n = useI18nStore();
const catalog = ref<PipelineCatalog | null>(null);
const runs = ref<PipelineRunTrace[]>([]);
const loading = ref(true);
const error = ref("");
const selectedKey = ref("");
const selectedTraceId = ref("");
const draft = ref<PipelineDefinition | null>(null);
const validation = ref<PipelineValidationResponse | null>(null);
const saving = ref(false);
const assigning = ref(false);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function keyFor(pipeline: PipelineDefinition) {
  return `${pipeline.pipeline_id}@${pipeline.version}`;
}
function featureForPurpose(purpose: string) {
  const map: Record<string, string> = {
    research: "research",
    evidence_suggestion: "evidence_suggestion.reviewer",
    metadata_precedents: "metadata_precedents",
    claim_memory: "claim_memory",
    response_memory: "response_memory",
  };
  return map[purpose] || "";
}
function purposeLabel(purpose: string) {
  const labels: Record<string, string> = {
    research: t("pipelines.purpose_research", "Research"),
    evidence_suggestion: t("pipelines.purpose_evidence", "Evidence suggestion"),
    metadata_precedents: t("pipelines.purpose_precedents", "Metadata precedents"),
    claim_memory: t("pipelines.purpose_claim_memory", "Claim memory"),
    response_memory: t("pipelines.purpose_response_memory", "Response memory"),
  };
  return labels[purpose] || purpose;
}
function definitionStatusLabel(status: PipelineDefinition["status"]) {
  const labels: Record<PipelineDefinition["status"], string> = {
    draft: t("pipelines.status_draft", "Draft"),
    active: t("pipelines.status_active", "Active"),
    disabled: t("pipelines.status_disabled", "Disabled"),
  };
  return labels[status];
}
function runStatusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: t("pipelines.status_completed", "Completed"),
    failed: t("pipelines.status_failed", "Failed"),
    cancelled: t("pipelines.status_cancelled", "Cancelled"),
    running: t("pipelines.status_running", "Running"),
  };
  return labels[status] || status;
}

const pipelines = computed(() => catalog.value?.pipelines || []);
const strategies = computed(() => catalog.value?.strategies || []);
const assignments = computed(() => catalog.value?.assignments || []);
const selectedPipeline = computed(() => {
  const match = pipelines.value.find((item) => keyFor(item) === selectedKey.value);
  return match || pipelines.value[0] || null;
});
const selectedTrace = computed(
  () => runs.value.find((run) => run.run_id === selectedTraceId.value) || runs.value[0] || null,
);
const selectedAssignment = computed(() => {
  const pipeline = selectedPipeline.value;
  if (!pipeline) return null;
  const feature = featureForPurpose(pipeline.purpose);
  return assignments.value.find((item) => item.feature === feature) || null;
});
const isSelectedAssigned = computed(() => {
  const pipeline = selectedPipeline.value;
  const assignment = selectedAssignment.value;
  return Boolean(
    pipeline &&
      assignment &&
      assignment.pipeline_id === pipeline.pipeline_id &&
      assignment.pipeline_version === pipeline.version,
  );
});
const canAssignSelected = computed(() => {
  const pipeline = selectedPipeline.value;
  return Boolean(
    pipeline &&
      pipeline.status === "active" &&
      pipeline.runtime_support?.supported &&
      featureForPurpose(pipeline.purpose),
  );
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [nextCatalog, tracePage] = await Promise.all([
      pipelinesApi.catalog(),
      pipelinesApi.runs({ limit: 30 }),
    ]);
    catalog.value = nextCatalog;
    runs.value = tracePage.runs || [];
    if (
      !selectedKey.value ||
      !nextCatalog.pipelines.some((item) => keyFor(item) === selectedKey.value)
    ) {
      const assignedResearch = nextCatalog.assignments.find((item) => item.feature === "research");
      const preferred = nextCatalog.pipelines.find(
        (item) =>
          item.pipeline_id === assignedResearch?.pipeline_id &&
          item.version === assignedResearch?.pipeline_version,
      );
      const fallback = preferred || nextCatalog.pipelines[0];
      selectedKey.value = fallback ? keyFor(fallback) : "";
    }
    if (
      runs.value.length &&
      (!selectedTraceId.value || !runs.value.some((item) => item.run_id === selectedTraceId.value))
    ) {
      selectedTraceId.value = runs.value[0].run_id;
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function beginClone() {
  const source = selectedPipeline.value;
  if (!source) return;
  const proposedId = source.built_in ? `${source.pipeline_id}.custom` : source.pipeline_id;
  const versions = pipelines.value
    .filter((item) => item.pipeline_id === proposedId)
    .map((item) => Number(item.version || 0));
  const nextVersion = Math.max(0, ...versions) + 1;
  draft.value = {
    ...JSON.parse(JSON.stringify(source)),
    pipeline_id: proposedId,
    version: nextVersion,
    name: source.built_in ? `${source.name} — custom` : source.name,
    status: "draft",
    built_in: false,
    derived_from: keyFor(source),
    created_at: null,
    created_by: null,
    validation: undefined,
    runtime_support: undefined,
  };
  validation.value = null;
}

async function validateDraft() {
  if (!draft.value) return;
  validation.value = await pipelinesApi.validate(draft.value);
}

async function saveDraft() {
  if (!draft.value || saving.value) return;
  saving.value = true;
  error.value = "";
  try {
    const checked = await pipelinesApi.validate(draft.value);
    validation.value = checked;
    // Runtime support gates activation/execution, not design work. Persisting a
    // graph-valid draft lets administrators version future adapters without
    // pretending the current runtime can execute them.
    if (!checked.validation.valid) return;
    const saved = await pipelinesApi.createDefinition(draft.value);
    draft.value = null;
    await load();
    selectedKey.value = keyFor(saved.pipeline);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}

async function assignSelected() {
  const pipeline = selectedPipeline.value;
  if (!pipeline || !canAssignSelected.value || assigning.value) return;
  const feature = featureForPurpose(pipeline.purpose);
  const current = assignments.value.find((item) => item.feature === feature);
  const assignment: PipelineAssignment = {
    feature,
    pipeline_id: pipeline.pipeline_id,
    pipeline_version: pipeline.version,
    scope: "system",
    scope_id: null,
    override_allowed: current?.override_allowed ?? feature === "research",
    source: "system",
  };
  assigning.value = true;
  error.value = "";
  try {
    await pipelinesApi.setAssignment(assignment);
    await load();
    selectedKey.value = keyFor(pipeline);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    assigning.value = false;
  }
}

async function resetSelectedAssignment() {
  const pipeline = selectedPipeline.value;
  if (!pipeline || assigning.value) return;
  const feature = featureForPurpose(pipeline.purpose);
  if (!feature) return;
  assigning.value = true;
  error.value = "";
  try {
    await pipelinesApi.resetAssignment(feature);
    await load();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    assigning.value = false;
  }
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(i18n.locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

onMounted(load);
</script>

<template>
  <div class="pipeline-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("pipelines.title", "Pipeline Studio") }}</h2>
        <p>
          {{
            t(
              "pipelines.help",
              "Inspect and version the registered retrieval, reranking, validation, and model chains DerridAI can execute.",
            )
          }}
        </p>
      </div>
      <button class="btn" type="button" :disabled="loading" @click="load">
        <AppIcon name="refresh" />
        {{ t("common.refresh", "Refresh") }}
      </button>
    </header>

    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div v-if="loading && !catalog" class="loading-card" role="status">
      {{ t("common.loading", "Loading…") }}
    </div>

    <template v-else-if="catalog">
      <section class="studio-grid" :aria-label="t('pipelines.definitions', 'Pipeline definitions')">
        <aside class="pipeline-browser">
          <div class="browser-heading">
            <div>
              <strong>{{ t("pipelines.definitions", "Pipeline definitions") }}</strong>
              <span>{{ pipelines.length }}</span>
            </div>
          </div>

          <button
            v-for="pipeline in pipelines"
            :key="keyFor(pipeline)"
            type="button"
            class="pipeline-choice"
            :class="{ selected: selectedKey === keyFor(pipeline) }"
            :aria-current="selectedKey === keyFor(pipeline) ? 'true' : undefined"
            @click="selectedKey = keyFor(pipeline)"
          >
            <span class="choice-top">
              <strong>{{ pipeline.name }}</strong>
              <small>v{{ pipeline.version }}</small>
            </span>
            <span class="choice-meta">
              {{ purposeLabel(pipeline.purpose) }}
              <span aria-hidden="true">·</span>
              {{ definitionStatusLabel(pipeline.status) }}
            </span>
            <span v-if="pipeline.built_in" class="choice-badge">
              {{ t("pipelines.built_in", "Built in") }}
            </span>
            <span
              v-if="
                assignments.some(
                  (item) =>
                    item.pipeline_id === pipeline.pipeline_id &&
                    item.pipeline_version === pipeline.version,
                )
              "
              class="choice-badge active"
            >
              {{ t("pipelines.assigned", "Assigned") }}
            </span>
          </button>
        </aside>

        <article v-if="selectedPipeline" class="pipeline-detail">
          <header class="detail-header">
            <div>
              <div class="detail-kicker">{{ purposeLabel(selectedPipeline.purpose) }}</div>
              <h3>{{ selectedPipeline.name }}</h3>
              <p>
                <code>{{ selectedPipeline.pipeline_id }}@{{ selectedPipeline.version }}</code>
                <span v-if="selectedPipeline.derived_from">
                  · {{ t("pipelines.derived_from", "derived from") }}
                  <code>{{ selectedPipeline.derived_from }}</code>
                </span>
              </p>
            </div>
            <div class="detail-actions">
              <button class="btn" type="button" @click="beginClone">
                <AppIcon name="copy" />
                {{ t("pipelines.clone", "Clone & edit") }}
              </button>
              <button
                class="btn primary"
                type="button"
                :disabled="!canAssignSelected || isSelectedAssigned || assigning"
                @click="assignSelected"
              >
                <AppIcon name="check" />
                {{
                  isSelectedAssigned
                    ? t("pipelines.active_assignment", "Active assignment")
                    : t("pipelines.assign", "Make active")
                }}
              </button>
            </div>
          </header>

          <div class="health-strip">
            <div>
              <span>{{ t("pipelines.graph_validation", "Graph validation") }}</span>
              <strong>
                {{
                  selectedPipeline.validation?.valid === false
                    ? t("pipelines.invalid", "Invalid")
                    : t("pipelines.valid", "Valid")
                }}
              </strong>
            </div>
            <div>
              <span>{{ t("pipelines.runtime_support", "Runtime support") }}</span>
              <strong>
                {{
                  selectedPipeline.runtime_support?.supported
                    ? t("pipelines.executable", "Executable")
                    : t("pipelines.inspect_only", "Inspect only")
                }}
              </strong>
            </div>
            <div>
              <span>{{ t("pipelines.assignment", "Assignment") }}</span>
              <strong>
                {{
                  isSelectedAssigned
                    ? t("pipelines.assigned", "Assigned")
                    : t("pipelines.not_assigned", "Not assigned")
                }}
              </strong>
            </div>
          </div>

          <p v-if="selectedPipeline.runtime_support?.reason" class="support-note">
            <AppIcon name="help" />
            {{ selectedPipeline.runtime_support.reason }}
          </p>

          <div
            v-if="selectedPipeline.validation?.issues?.length"
            class="validation-issues"
            :aria-label="t('pipelines.validation_issues', 'Validation issues')"
          >
            <p
              v-for="issue in selectedPipeline.validation.issues"
              :key="`${issue.code}:${issue.stage_id || ''}`"
              :data-level="issue.level"
            >
              <AppIcon :name="issue.level === 'error' ? 'warning' : 'help'" />
              <span>{{ issue.message }}</span>
            </p>
          </div>

          <PipelineStageList :pipeline="selectedPipeline" :strategies="strategies" />

          <footer
            v-if="selectedAssignment && selectedAssignment.source !== 'built_in'"
            class="assignment-footer"
          >
            <div>
              <strong>{{ t("pipelines.custom_assignment", "Custom system assignment") }}</strong>
              <span>
                {{ selectedAssignment.feature }} · {{ selectedAssignment.pipeline_id }}@{{
                  selectedAssignment.pipeline_version
                }}
              </span>
            </div>
            <button
              class="btn"
              type="button"
              :disabled="assigning"
              @click="resetSelectedAssignment"
            >
              {{ t("pipelines.restore_default", "Restore built-in default") }}
            </button>
          </footer>
        </article>
      </section>

      <section v-if="draft" class="editor-card" aria-labelledby="pipeline-editor-title">
        <header class="editor-heading">
          <div>
            <div class="detail-kicker">
              {{ t("pipelines.new_version", "New pipeline version") }}
            </div>
            <h3 id="pipeline-editor-title">
              {{ t("pipelines.configure_clone", "Configure cloned pipeline") }}
            </h3>
          </div>
          <button class="btn" type="button" @click="draft = null">
            {{ t("common.cancel", "Cancel") }}
          </button>
        </header>

        <PipelineDefinitionEditor v-model="draft" :strategies="strategies" />

        <div v-if="validation" class="validation-result" :data-valid="validation.validation.valid">
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
          <button class="btn" type="button" :disabled="saving" @click="validateDraft">
            {{ t("pipelines.validate", "Validate") }}
          </button>
          <button class="btn primary" type="button" :disabled="saving" @click="saveDraft">
            <AppIcon name="check" />
            {{
              saving
                ? t("pipelines.saving", "Saving…")
                : t("pipelines.save_version", "Save version")
            }}
          </button>
        </footer>
      </section>

      <section class="trace-workspace" aria-labelledby="pipeline-runs-title">
        <header class="trace-workspace-heading">
          <div>
            <h3 id="pipeline-runs-title">{{ t("pipelines.recent_runs", "Recent executions") }}</h3>
            <p>
              {{
                t(
                  "pipelines.recent_runs_help",
                  "Trace the strategy path, fallbacks, candidate counts, models, collections, and timings that actually ran.",
                )
              }}
            </p>
          </div>
        </header>

        <div v-if="runs.length" class="trace-grid">
          <div
            class="run-list"
            role="list"
            :aria-label="t('pipelines.recent_runs', 'Recent executions')"
          >
            <button
              v-for="run in runs"
              :key="run.run_id"
              type="button"
              :class="{ selected: selectedTrace?.run_id === run.run_id }"
              @click="selectedTraceId = run.run_id"
            >
              <span>
                <strong>{{ run.pipeline_id }} v{{ run.pipeline_version }}</strong>
                <small>{{ run.feature }}</small>
              </span>
              <span>
                <strong>{{ runStatusLabel(run.status) }}</strong>
                <small>{{ formatDate(run.started_at) }}</small>
              </span>
            </button>
          </div>
          <PipelineRunTracePanel v-if="selectedTrace" :trace="selectedTrace" />
        </div>
        <div v-else class="empty-state">
          <AppIcon name="history" />
          <div>
            <strong>{{ t("pipelines.no_runs", "No pipeline traces yet") }}</strong>
            <p>
              {{
                t(
                  "pipelines.no_runs_help",
                  "New Research runs will appear here once they complete.",
                )
              }}
            </p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.pipeline-workspace {
  display: grid;
  gap: 18px;
}
.workspace-heading,
.detail-header,
.editor-heading,
.trace-workspace-heading,
.assignment-footer {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}
.workspace-heading h2,
.detail-header h3,
.editor-heading h3,
.trace-workspace-heading h3 {
  margin: 0;
}
.workspace-heading h2 {
  font-size: 1.25rem;
}
.workspace-heading p,
.trace-workspace-heading p {
  max-width: 780px;
  margin: 5px 0 0;
  color: var(--muted);
  line-height: 1.5;
}
.workspace-heading :deep(svg),
.detail-actions :deep(svg),
.support-note :deep(svg),
.validation-issues :deep(svg),
.editor-actions :deep(svg),
.empty-state :deep(svg) {
  width: 15px;
  height: 15px;
}
.error-banner,
.loading-card,
.support-note,
.validation-result,
.empty-state {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.error-banner {
  border-color: color-mix(in srgb, var(--line) 60%, currentColor);
}
.studio-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.34fr) minmax(0, 1fr);
  gap: 14px;
}
.pipeline-browser,
.pipeline-detail,
.editor-card,
.trace-workspace {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.pipeline-browser {
  align-self: start;
  overflow: hidden;
}
.browser-heading {
  padding: 12px;
  border-bottom: 1px solid var(--line);
}
.browser-heading > div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.browser-heading span {
  color: var(--muted);
  font-size: 0.78rem;
}
.pipeline-choice {
  position: relative;
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 12px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.pipeline-choice:last-child {
  border-bottom: 0;
}
.pipeline-choice:hover,
.pipeline-choice.selected {
  background: var(--soft);
}
.pipeline-choice.selected::before {
  position: absolute;
  inset: 8px auto 8px 0;
  width: 3px;
  border-radius: 999px;
  background: currentColor;
  content: "";
}
.choice-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.choice-top strong {
  font-size: 0.82rem;
}
.choice-top small,
.choice-meta {
  color: var(--muted);
  font-size: 0.72rem;
}
.choice-badge {
  justify-self: start;
  margin-top: 3px;
  padding: 2px 6px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 750;
}
.choice-badge.active {
  color: inherit;
}
.pipeline-detail {
  display: grid;
  gap: 14px;
  padding: 16px;
}
.detail-kicker {
  margin-bottom: 3px;
  color: var(--muted);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.detail-header h3,
.editor-heading h3,
.trace-workspace-heading h3 {
  font-size: 1rem;
}
.detail-header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.76rem;
}
.detail-actions,
.editor-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.health-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.health-strip > div {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
  border-right: 1px solid var(--line);
}
.health-strip > div:last-child {
  border-right: 0;
}
.health-strip span {
  color: var(--muted);
  font-size: 0.68rem;
}
.health-strip strong {
  font-size: 0.78rem;
}
.support-note {
  display: flex;
  gap: 8px;
  margin: 0;
  color: var(--muted);
  font-size: 0.77rem;
  line-height: 1.45;
}
.support-note :deep(svg) {
  flex: 0 0 auto;
  margin-top: 1px;
}
.validation-issues {
  display: grid;
  gap: 6px;
}
.validation-issues p {
  display: flex;
  gap: 7px;
  margin: 0;
  color: var(--muted);
  font-size: 0.76rem;
}
.validation-issues p[data-level="error"] {
  color: inherit;
}
.assignment-footer {
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.assignment-footer > div {
  display: grid;
  gap: 2px;
}
.assignment-footer strong {
  font-size: 0.8rem;
}
.assignment-footer span {
  color: var(--muted);
  font-size: 0.72rem;
}
.editor-card,
.trace-workspace {
  display: grid;
  gap: 16px;
  padding: 16px;
}
.validation-result {
  display: grid;
  gap: 4px;
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
  justify-content: end;
  padding-top: 4px;
}
.trace-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.35fr) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.run-list {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 12px;
}
.run-list button {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 11px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.run-list button:last-child {
  border-bottom: 0;
}
.run-list button:hover,
.run-list button.selected {
  background: var(--soft);
}
.run-list button span {
  display: grid;
  gap: 2px;
}
.run-list button span:last-child {
  justify-items: end;
  text-align: right;
}
.run-list strong {
  font-size: 0.73rem;
}
.run-list small {
  color: var(--muted);
  font-size: 0.66rem;
}
.empty-state {
  display: flex;
  gap: 10px;
  align-items: start;
}
.empty-state p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
}
@media (max-width: 960px) {
  .studio-grid,
  .trace-grid {
    grid-template-columns: 1fr;
  }
  .pipeline-browser {
    max-height: 300px;
    overflow: auto;
  }
}
@media (max-width: 680px) {
  .workspace-heading,
  .detail-header,
  .editor-heading,
  .assignment-footer {
    display: grid;
  }
  .health-strip {
    grid-template-columns: 1fr;
  }
  .health-strip > div {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .health-strip > div:last-child {
    border-bottom: 0;
  }
  .editor-actions {
    justify-content: stretch;
  }
  .editor-actions .btn {
    flex: 1;
  }
}
</style>

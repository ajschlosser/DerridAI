<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { toast } from "../composables/notifications";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import ResearchThreadBrowser from "../components/research/ResearchThreadBrowser.vue";
import type { ResearchTurn } from "../types/researchThreads";
import ResearchComposer from "../components/research/ResearchComposer.vue";
import ResearchResultPresentation from "../components/research/ResearchResultPresentation.vue";
import ResearchSettingsDrawer from "../components/research/ResearchSettingsDrawer.vue";
import ResearchRunsDrawer from "../components/research/ResearchRunsDrawer.vue";
import ResearchPipelineBar from "../components/research/ResearchPipelineBar.vue";
import { useResearchDraft } from "../features/research/useResearchDraft";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import type {
  ResearchConfig,
  ResearchJob,
  ResearchProfile,
  ResearchWorkspaceSnapshot,
} from "../types/research";
import type { PipelineConfigOverrideSet } from "../types/pipelines";
import * as researchActions from "../domain/researchActions";
import { annotationsWorkspace } from "../domain/sharedAnnotations";
import { pipelinesApi } from "../api/pipelines";
import { normalizedResearchConfig } from "../domain/researchPayloads";
import { overridesForPipeline, setStageOverride } from "../domain/pipelineOverrides";
import { getResearchJob } from "../domain/sharedResearchJobs";
import { openDatabaseCreationFromResearch } from "../domain/databaseCreationRequest";
import { followResource } from "../realtime/follow";
import UiPageHeader from "../components/ui/UiPageHeader.vue";

const route = useRoute();
const threadBrowserOpen = ref(false);
const newQuestionRequested = ref(false);
const currentThreadId = computed(() => String(route.query.thread || ""));
watch(
  currentThreadId,
  (id) => {
    if (id) threadBrowserOpen.value = true;
  },
  { immediate: true },
);
async function selectThread(id: string) {
  await router.push({ path: "/rag", query: { thread: id } });
}
async function openThreadTurn(turn: ResearchTurn) {
  if (turn.job_id)
    await router.push({ path: "/rag", query: { thread: turn.thread_id, job: turn.job_id } });
}
async function onThreadRemoved(error?: string) {
  await newThread();
  if (error) toast(error, { tone: "danger" });
}
async function newThread() {
  newQuestionRequested.value = true;
  await router.push({ path: "/rag" });
  activeJob.value = null;
  prompt.value = "";
  instructions.value = "";
  await nextTick();
  document.getElementById("researchQuestion")?.focus();
}
function evidenceTarget(index: number) {
  const item = activeResult.value?.evidence?.[index];
  const recordId = String(item?.record?.record_id || "").trim();
  const store = String(item?.collection || "").trim();
  return recordId ? { recordId, store } : null;
}
function openEvidenceRecord(index: number) {
  const target = evidenceTarget(index);
  if (!target) return;
  annotationsWorkspace.openAnnotationsWorkspaceRecord({
    server: true,
    source: target.store,
    record_id: target.recordId,
  });
}
function openEvidenceRelationships(index: number, mode: "trace" | "model") {
  const target = evidenceTarget(index);
  if (!target) return;
  void router.push({
    name: "relationships",
    query: { record: target.recordId, store: target.store, mode },
  });
}
const router = useRouter();
const auth = useAuthStore();
const i18n = useI18nStore();
const isNativeResearch = computed(() => route.name === "rag");
const loading = ref(false);
const noDatabase = ref(false);
const workspaceError = ref("");
const answerLoading = ref(false);
const answerError = ref("");
const runsLoading = ref(false);
const runsError = ref("");
const pipelinesLoading = ref(false);
const pipelinesError = ref("");
let runsRequest = 0;
let pipelinesRequest = 0;
let workspaceRequest = 0;
let answerRequest = 0;
let disposed = false;
const canCreateDatabase = computed(() => auth.can("page.vector"));
const starting = ref(false);
const workspace = ref<ResearchWorkspaceSnapshot | null>(null);
const config = ref<ResearchConfig | null>(null);
const runPipelineOverrides = ref<PipelineConfigOverrideSet | null>(null);
const prompt = ref("");
const instructions = ref("");
const preset = ref("balanced");
const model = ref("");
const discoveredModels = ref<string[]>([]);
const generation = ref<Record<string, unknown>>({});
const jobs = ref<ResearchJob[]>([]);
const activeJob = ref<ResearchJob | null>(null);
const sessionJobIds = ref<Set<string>>(new Set());
const threadRefreshKey = ref(0);
const retryFocusJob = ref("");
let submissionRequest = 0;
const activeEvidenceIndex = ref(0);
const settingsDrawer = ref<{
  open: (
    section?: "pipeline" | "retrieval" | "evidence" | "generation",
    focusPromptMetadata?: boolean,
  ) => void;
} | null>(null);
const runsDrawer = ref<{ open: () => void; close: () => void } | null>(null);
const researchDraft = useResearchDraft();
// One realtime follower per live Research job; its events (or the socket-down fallback) refresh state.
const jobFollowers = new Map<string, () => void>();
let draftTimer: number | undefined;

const selectedEvidence = computed(() => workspace.value?.selected_evidence || []);
const profiles = computed(() => workspace.value?.profiles || []);
const stores = computed(() => workspace.value?.stores || []);
const effectivePipeline = computed(() => {
  const options = workspace.value?.pipeline_options || [];
  const configuredId = String(config.value?.pipeline_id || "").trim();
  const configuredVersion = Number(config.value?.pipeline_version || 0);
  if (configuredId) {
    const explicit = options.find(
      (pipeline) => pipeline.pipeline_id === configuredId && pipeline.version === configuredVersion,
    );
    if (explicit) return explicit;
  }
  const assignment = workspace.value?.pipeline_assignment;
  return (
    options.find(
      (pipeline) =>
        pipeline.pipeline_id === assignment?.pipeline_id &&
        pipeline.version === assignment?.pipeline_version,
    ) || null
  );
});
const pipelineOverrideActive = computed(() =>
  Boolean(String(config.value?.pipeline_id || "").trim()),
);
const settingsPipelineOverrides = computed(() =>
  overridesForPipeline(config.value?.pipeline_config_overrides, effectivePipeline.value),
);
const metadataFields = computed(() => {
  const fields = new Set<string>();
  const selectedStore = stores.value.find(
    (store) => store.name === config.value?.source_collection,
  );
  for (const field of selectedStore?.filter_fields || []) fields.add(String(field));
  for (const item of selectedEvidence.value) {
    for (const assertion of item.assertions || []) {
      if (assertion.field_name) fields.add(assertion.field_name);
      else if (assertion.field_id) fields.add(assertion.field_id);
    }
    for (const field of Object.keys(item.metadata || {})) fields.add(field);
  }
  for (const scope of ["evidence", "context", "record"] as const) {
    for (const field of config.value?.prompt_metadata?.[scope] || []) fields.add(field);
  }
  for (const field of [
    "speaker",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "position_holder",
    "stance",
    "proposition_status",
    "target",
    "discourse_role",
  ]) {
    fields.add(field);
  }
  return [...fields]
    .filter((field) => field && !field.startsWith("_"))
    .sort((a, b) => a.localeCompare(b));
});
const activeResult = computed(() => activeJob.value?.result || null);
const selectedProfile = computed(
  () =>
    profiles.value.find((profile) => profile.id === config.value?.provider_profile_id) ||
    profiles.value[0] ||
    null,
);
const canManageRuns = computed(
  () =>
    Boolean(workspace.value) &&
    (Boolean(workspace.value?.can_manage_jobs && auth.can("rag.jobs.own")) || auth.isAdmin),
);
const canConfigureResearch = computed(() =>
  Boolean(workspace.value?.can_run && auth.can("rag.run")),
);
const canGrade = computed(() => auth.isAdmin);
const runDisabledReason = computed(() => {
  if (currentThreadId.value) return i18n.t("research.thread_context_pending");
  if (!workspace.value?.can_run || !auth.can("rag.run")) return i18n.t("permissions.rag_denied");
  if (!prompt.value.trim()) return i18n.t("research.prompt_required");
  if (!profiles.value.length) return i18n.t("research.no_profile_configured");
  if (preset.value === "evidence" && !selectedEvidence.value.length)
    return i18n.t("research.evidence_required");
  if (preset.value !== "evidence" && !config.value?.source_collection && !stores.value.length)
    return i18n.t("research.database_required");
  return "";
});
const canRun = computed(() => !runDisabledReason.value);

function profileGeneration(profile: ResearchProfile | null) {
  if (!profile) return {};
  return {
    num_ctx: profile.num_ctx ?? null,
    num_predict: profile.num_predict ?? 4096,
    think: profile.think ?? "false",
    temperature: profile.temperature ?? 0,
    top_k: profile.top_k ?? 0,
    top_p: profile.top_p ?? 1,
    min_p: profile.min_p ?? null,
    repeat_penalty: profile.repeat_penalty ?? 1.1,
    seed: profile.seed ?? null,
    mirostat: profile.mirostat ?? 0,
    mirostat_eta: profile.mirostat_eta ?? null,
    mirostat_tau: profile.mirostat_tau ?? null,
    keep_alive: profile.keep_alive ?? "10m",
    extra_options: profile.extra_options ?? "{}",
  };
}
function profileModel(profile: ResearchProfile | null) {
  if (!profile) return "";
  return profile.type === "openai" && profile.model_mode === "auto"
    ? "auto"
    : String(profile.model || "");
}
function inferPreset(cfg: ResearchConfig) {
  if (cfg.skip_retrieval) return "evidence";
  if (cfg.k === 40 && cfg.fetch_k === 320 && cfg.rerank_top_n === 16) return "precision";
  if (cfg.k === 96 && cfg.fetch_k === 1000 && cfg.rerank_top_n === 32) return "recall";
  if (
    cfg.k === 64 &&
    cfg.fetch_k === 500 &&
    cfg.rerank_top_n === 24 &&
    Math.abs(Number(cfg.lambda_mult) - 0.7) < 0.001
  )
    return "balanced";
  return "custom";
}
function hydrate(
  snapshot: ResearchWorkspaceSnapshot,
  { preserveDraft = false, preserveActive = true } = {},
) {
  workspace.value = workspace.value
    ? {
        ...snapshot,
        pipeline_assignment: workspace.value.pipeline_assignment,
        pipeline_options: workspace.value.pipeline_options,
        pipeline_strategies: workspace.value.pipeline_strategies,
        pipeline_override_allowed: workspace.value.pipeline_override_allowed,
      }
    : snapshot;
  const snapshotJobs = snapshot.jobs || [];
  if (snapshot.can_manage_jobs || auth.isAdmin) {
    jobs.value = snapshotJobs;
  } else {
    const retained = jobs.value.filter((job) => sessionJobIds.value.has(job.id));
    const merged = [...snapshotJobs, ...retained].filter(
      (job, index, all) => all.findIndex((candidate) => candidate.id === job.id) === index,
    );
    jobs.value = merged;
  }
  config.value = { ...snapshot.config };
  if (!preserveDraft) {
    prompt.value = String(snapshot.config.prompt || "");
    instructions.value = String(snapshot.config.instructions || "");
    preset.value = inferPreset(snapshot.config);
  }
  const profile =
    snapshot.profiles.find((item) => item.id === snapshot.config.provider_profile_id) ||
    snapshot.profiles[0] ||
    null;
  if (!preserveDraft || !model.value) {
    model.value = profileModel(profile);
    generation.value = profileGeneration(profile);
  }
  if (preserveActive && activeJob.value) {
    const updated = jobs.value.find((job) => job.id === activeJob.value?.id);
    if (updated)
      activeJob.value = {
        ...activeJob.value,
        ...updated,
        result: activeJob.value.result || updated.result,
      };
  } else if (!activeJob.value) {
    activeJob.value =
      jobs.value.find((job) => ["queued", "running", "cancelling"].includes(job.status)) ||
      jobs.value.find((job) => job.status === "completed") ||
      null;
  }
}
async function loadWorkspace(refresh = true) {
  if (!isNativeResearch.value || disposed) return;
  const request = ++workspaceRequest;
  ++runsRequest;
  ++pipelinesRequest;
  loading.value = true;
  workspaceError.value = "";
  try {
    const snapshot = (await researchActions.getResearchWorkspaceSnapshot({
      refresh,
      includeJobs: false,
      includePipelines: false,
      strictCollections: true,
    })) as ResearchWorkspaceSnapshot;
    if (disposed || request !== workspaceRequest || !isNativeResearch.value) return;
    noDatabase.value = !(snapshot.stores || []).length;
    hydrate(snapshot, {
      preserveDraft: Boolean(workspace.value) || Boolean(prompt.value || instructions.value),
      preserveActive: true,
    });
    if (canManageRuns.value) void refreshRuns();
    void loadPipelines();
    const requestedJobId = String(route.query.job || "").trim();
    if (requestedJobId) {
      void loadAnswer({ id: requestedJobId, status: "completed" } as ResearchJob);
    } else if (activeJob.value?.status === "completed" && !activeJob.value.result) {
      void loadAnswer(activeJob.value);
    }
    schedulePoll();
  } catch (error) {
    if (!disposed && request === workspaceRequest)
      workspaceError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (!disposed && request === workspaceRequest) loading.value = false;
  }
}
async function loadAnswer(job: ResearchJob) {
  const request = ++answerRequest;
  // Different answers must never retain the previous answer's text or evidence.
  const sameJob = activeJob.value?.id === job.id;
  if (!sameJob) activeJob.value = { ...job, result: undefined };
  activeEvidenceIndex.value = 0;
  answerLoading.value = true;
  answerError.value = "";
  try {
    const answer =
      job.status === "completed" ? ((await getResearchJob(job.id)) as ResearchJob) : job;
    if (disposed || request !== answerRequest || !isNativeResearch.value) return;
    activeJob.value = answer;
    if (!jobs.value.some((item) => item.id === answer.id)) jobs.value = [answer, ...jobs.value];
    runsDrawer.value?.close();
    schedulePoll();
  } catch (error) {
    if (!disposed && request === answerRequest)
      answerError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (!disposed && request === answerRequest) answerLoading.value = false;
  }
}
function persistDraft() {
  if (!config.value) return;
  window.clearTimeout(draftTimer);
  draftTimer = window.setTimeout(
    () =>
      researchActions.updateResearchConfig({
        prompt: prompt.value,
        instructions: instructions.value,
      }),
    250,
  );
}
function updateConfig(patch: Partial<ResearchConfig>) {
  if (!config.value) return;
  // Controls on Research are a one-run draft. Settings owns persisted defaults.
  config.value = { ...config.value, ...patch };
}
function applyPresetStageOverrides(values: {
  fetchK: number;
  lambdaMult: number;
  rrfK: number;
  rerankTopN: number;
}) {
  const pipeline = effectivePipeline.value;
  if (!pipeline) return;
  let overrides = runPipelineOverrides.value;
  for (const stage of pipeline.stages) {
    if (
      stage.strategy === "retrieve.chroma_similarity" ||
      stage.strategy === "retrieve.lexical_bm25"
    )
      overrides = setStageOverride(pipeline, overrides, stage.id, "fetch_k", values.fetchK);
    else if (stage.strategy === "select.mmr")
      overrides = setStageOverride(pipeline, overrides, stage.id, "lambda_mult", values.lambdaMult);
    else if (stage.strategy === "fusion.rrf")
      overrides = setStageOverride(pipeline, overrides, stage.id, "rrf_k", values.rrfK);
    else if (stage.strategy === "rerank.cross_encoder")
      overrides = setStageOverride(pipeline, overrides, stage.id, "top_k", values.rerankTopN);
  }
  runPipelineOverrides.value = overrides;
}
function applyPreset(value: string) {
  preset.value = value;
  if (!config.value) return;
  if (value === "evidence") {
    if (!selectedEvidence.value.length) {
      preset.value = "balanced";
      return;
    }
    updateConfig({ skip_retrieval: true });
    return;
  }
  if (value === "hybrid" && !selectedEvidence.value.length) {
    preset.value = "balanced";
    return;
  }
  // Hybrid = balanced retrieval plus the researcher's pinned evidence. Presets
  // now express stage tuning as one-run overrides rather than mutating Settings.
  const common = {
    skip_retrieval: false,
    search_types: ["similarity", "lexical", "mmr"],
  };
  if (value === "balanced" || value === "hybrid") {
    updateConfig({ ...common, k: 64 });
    applyPresetStageOverrides({ fetchK: 500, lambdaMult: 0.7, rrfK: 60, rerankTopN: 24 });
  } else if (value === "precision") {
    updateConfig({ ...common, k: 40 });
    applyPresetStageOverrides({ fetchK: 320, lambdaMult: 0.82, rrfK: 60, rerankTopN: 16 });
  } else if (value === "recall") {
    updateConfig({ ...common, k: 96 });
    applyPresetStageOverrides({ fetchK: 1000, lambdaMult: 0.58, rrfK: 60, rerankTopN: 32 });
  }
}
function changeProfile(id: string) {
  updateConfig({ provider_profile_id: id });
  const profile = profiles.value.find((item) => item.id === id) || null;
  model.value = profileModel(profile);
  generation.value = profileGeneration(profile);
  discoveredModels.value = profile?.model ? [String(profile.model)] : [];
}
async function runResearch(turn?: ResearchTurn) {
  if (!config.value || starting.value || !workspace.value?.can_run || !auth.can("rag.run")) return;
  if (turn) {
    if (turn.thread_id !== currentThreadId.value || !["failed", "cancelled"].includes(turn.status))
      return;
  } else {
    if (!canRun.value) return;
    if (route.query.job) await router.replace({ path: "/rag" });
  }
  const request = ++submissionRequest;
  ++answerRequest;
  answerLoading.value = false;
  answerError.value = "";
  starting.value = true;
  newQuestionRequested.value = false;
  try {
    persistDraft();
    const job = (await researchActions.startResearchRun({
      prompt: turn?.user_question ?? prompt.value,
      instructions: turn ? turn.user_instructions || "" : instructions.value,
      retry_thread_id: turn?.thread_id,
      retry_turn_id: turn?.turn_id,
      provider_profile_id: config.value.provider_profile_id,
      model: model.value,
      generation: generation.value,
      skip_retrieval: preset.value === "evidence" || config.value.skip_retrieval,
      config: { ...config.value, prompt: prompt.value, instructions: instructions.value },
      settings_pipeline_overrides: settingsPipelineOverrides.value,
      run_pipeline_overrides: runPipelineOverrides.value,
    })) as ResearchJob;
    if (disposed || request !== submissionRequest) return;
    sessionJobIds.value.add(job.id);
    activeJob.value = job;
    activeEvidenceIndex.value = 0;
    jobs.value = [job, ...jobs.value.filter((item) => item.id !== job.id)];
    schedulePoll(true);
    if (turn) retryFocusJob.value = job.id;
    if (job.thread_id) {
      await router.push({ path: "/rag", query: { thread: job.thread_id, job: job.id } });
    }
    await nextTick();
    document
      .querySelector(".research-answer-workspace")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    if (request === submissionRequest)
      toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  } finally {
    if (request === submissionRequest) {
      starting.value = false;
      if (turn) ++threadRefreshKey.value;
    }
  }
}
async function refreshLiveJobs() {
  if (!isNativeResearch.value || disposed) return;
  const request = answerRequest;
  try {
    if (canManageRuns.value) {
      const refreshed = (await researchActions.refreshResearchJobs()) as ResearchJob[];
      if (disposed || request !== answerRequest || !isNativeResearch.value) return;
      jobs.value = refreshed;
      if (activeJob.value) {
        const summary = refreshed.find((job) => job.id === activeJob.value?.id);
        if (summary) {
          activeJob.value = {
            ...activeJob.value,
            ...summary,
            result: activeJob.value.result || summary.result,
          };
          if (["completed", "failed", "cancelled"].includes(summary.status)) {
            const completed = (await getResearchJob(summary.id)) as ResearchJob;
            if (!disposed && request === answerRequest && activeJob.value?.id === summary.id)
              activeJob.value = completed;
          }
        }
      }
    } else {
      // A role may be allowed to run Research without being allowed to browse
      // retained job history. Track every run started in this browser session
      // independently so the workspace never collapses back to a single pipeline.
      const activeSessionJobs = jobs.value.filter(
        (job) =>
          sessionJobIds.value.has(job.id) &&
          ["queued", "running", "cancelling"].includes(job.status),
      );
      if (activeSessionJobs.length) {
        const refreshed = await Promise.all(
          activeSessionJobs.map((job) => getResearchJob(job.id) as Promise<ResearchJob>),
        );
        if (disposed || request !== answerRequest || !isNativeResearch.value) return;
        const byId = new Map(refreshed.map((job) => [job.id, job]));
        jobs.value = jobs.value.map((job) => byId.get(job.id) || job);
        if (activeJob.value && byId.has(activeJob.value.id))
          activeJob.value = byId.get(activeJob.value.id) || activeJob.value;
      }
    }
  } catch (error) {
    if (!disposed && request === answerRequest)
      runsError.value = error instanceof Error ? error.message : String(error);
  }
  schedulePoll();
}
const LIVE_STATUSES = ["queued", "running", "cancelling"];
function schedulePoll(force = false) {
  const live = new Set<string>();
  if (isNativeResearch.value) {
    for (const job of [activeJob.value, ...jobs.value])
      if (job && LIVE_STATUSES.includes(job.status)) live.add(job.id);
    // A just-started run is followed even before its first status is known.
    if (force && activeJob.value) live.add(activeJob.value.id);
  }
  for (const [id, stop] of jobFollowers) {
    if (live.has(id)) continue;
    stop();
    jobFollowers.delete(id);
  }
  for (const id of live) {
    if (jobFollowers.has(id)) continue;
    jobFollowers.set(
      id,
      followResource({ topic: `job:${id}`, refresh: refreshLiveJobs, minIntervalMs: 1000 }),
    );
  }
}
function stopJobFollowers() {
  for (const stop of jobFollowers.values()) stop();
  jobFollowers.clear();
}
async function openJob(job: ResearchJob) {
  if (route.query.job) await router.replace({ path: "/rag" });
  await loadAnswer(job);
}
async function cancelJob(job: ResearchJob) {
  try {
    const updated = (await researchActions.cancelResearchJob(job.id)) as ResearchJob;
    if (activeJob.value?.id === job.id) activeJob.value = updated;
    await refreshRuns();
  } catch (error) {
    toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function removeJob(job: ResearchJob) {
  if (!window.confirm(i18n.t("research.remove_run_confirm"))) return;
  try {
    await researchActions.deleteResearchJob(job.id);
    if (activeJob.value?.id === job.id) activeJob.value = null;
    await refreshRuns();
  } catch (error) {
    toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function refreshRuns() {
  const request = ++runsRequest;
  runsLoading.value = true;
  runsError.value = "";
  try {
    const refreshed = (await researchActions.refreshResearchJobs()) as ResearchJob[];
    if (disposed || request !== runsRequest || !isNativeResearch.value) return;
    jobs.value = refreshed;
    if (!activeJob.value && !currentThreadId.value && !newQuestionRequested.value) {
      const candidate =
        refreshed.find((job) => ["queued", "running", "cancelling"].includes(job.status)) ||
        refreshed.find((job) => job.status === "completed");
      if (candidate) void loadAnswer(candidate);
    }
    schedulePoll();
  } catch (error) {
    if (!disposed && request === runsRequest)
      runsError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (!disposed && request === runsRequest) runsLoading.value = false;
  }
}
async function loadPipelines() {
  const request = ++pipelinesRequest;
  pipelinesLoading.value = true;
  pipelinesError.value = "";
  try {
    const options = await pipelinesApi.researchOptions();
    if (disposed || request !== pipelinesRequest || !workspace.value || !isNativeResearch.value)
      return;
    const configuredId = String(config.value?.pipeline_id || "").trim();
    const configuredVersion = Number(config.value?.pipeline_version || 0);
    if (
      configuredId &&
      !options.pipelines.some(
        (pipeline) =>
          pipeline.pipeline_id === configuredId && pipeline.version === configuredVersion,
      )
    ) {
      updateConfig({ pipeline_id: "", pipeline_version: null });
    }
    workspace.value = {
      ...workspace.value,
      pipeline_assignment: options.assignment,
      pipeline_options: options.pipelines,
      pipeline_strategies: options.strategies,
      pipeline_override_allowed: options.override_allowed,
    };
  } catch (error) {
    if (!disposed && request === pipelinesRequest)
      pipelinesError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (!disposed && request === pipelinesRequest) pipelinesLoading.value = false;
  }
}
function loadHistory(item: Record<string, unknown>) {
  prompt.value = String(item.prompt || "");
  instructions.value = String(item.instructions || "");
  persistDraft();
  toast(i18n.t("research.question_restored"), {
    tone: "success",
  });
}
function removeEvidence(key: string) {
  try {
    const evidence = researchActions.removeResearchEvidence(key);
    if (workspace.value) workspace.value = { ...workspace.value, selected_evidence: evidence };
    if (!evidence.length && preset.value === "evidence") applyPreset("balanced");
  } catch (error) {
    toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
function clearEvidence() {
  try {
    researchActions.clearResearchEvidence();
    if (workspace.value) workspace.value = { ...workspace.value, selected_evidence: [] };
    if (config.value) config.value = { ...config.value, skip_retrieval: false };
    if (preset.value === "evidence") preset.value = "balanced";
  } catch (error) {
    toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function copyAnswer() {
  try {
    await navigator.clipboard.writeText(activeResult.value?.answer || "");
    toast(i18n.t("research.answer_copied"), { tone: "success" });
  } catch {
    toast(i18n.t("research.clipboard_failed"), {
      tone: "danger",
    });
  }
}
function focusEvidence(index: number) {
  activeEvidenceIndex.value = index;
  if (window.matchMedia("(max-width: 860px)").matches)
    void nextTick(() =>
      document
        .querySelector("#researchEvidencePanel")
        ?.scrollIntoView({ behavior: "smooth", block: "start" }),
    );
}
async function gradeAnswer() {
  if (!activeJob.value) return;
  try {
    await researchActions.gradeResearchJob(activeJob.value.id);
  } catch (error) {
    toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
function prepareRerun() {
  if (!activeJob.value) return;
  newQuestionRequested.value = true;
  if (route.query.job || currentThreadId.value) void router.replace({ path: "/rag" });
  const next = researchActions.prepareResearchRerun(activeJob.value) as ResearchConfig;
  config.value = { ...next };
  runPipelineOverrides.value = next.run_pipeline_overrides || null;
  prompt.value = next.prompt || "";
  instructions.value = next.instructions || "";
  preset.value = inferPreset(next);
  const profile =
    profiles.value.find((item) => item.id === next.provider_profile_id) || selectedProfile.value;
  model.value = profileModel(profile || null);
  generation.value = profileGeneration(profile || null);
  activeJob.value = null;
  toast(i18n.t("research.rerun_loaded"), {
    tone: "success",
  });
  void nextTick(() => document.querySelector<HTMLTextAreaElement>("#researchQuestion")?.focus());
}
async function discoverModels() {
  if (!config.value) return;
  try {
    discoveredModels.value = (await researchActions.discoverResearchModels(
      config.value.provider_profile_id,
    )) as string[];
    toast(`${discoveredModels.value.length} ${i18n.t("research.models_found")}`, {
      tone: "success",
    });
  } catch (error) {
    toast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
function applySettings(payload: {
  config: Partial<ResearchConfig>;
  generation: Record<string, unknown>;
  model: string;
  runPipelineOverrides: PipelineConfigOverrideSet | null;
}) {
  updateConfig(payload.config);
  runPipelineOverrides.value = payload.runPipelineOverrides;
  generation.value = { ...payload.generation };
  model.value = payload.model || profileModel(selectedProfile.value);
  preset.value = "custom";
  toast(i18n.t("research.settings_applied"), {
    tone: "success",
  });
}

watch(prompt, persistDraft);
watch(instructions, persistDraft);
// Follow the running job's streamed answer only while it has no authoritative result yet;
// any other state (finished, failed, cancelled, or nothing selected) drops the draft.
watch(
  activeJob,
  (job) => {
    const live = Boolean(
      job && !job.result && ["queued", "running", "cancelling"].includes(job.status),
    );
    if (live && job && researchDraft.draft.value?.jobId !== job.id) researchDraft.follow(job.id);
    else if (!live) researchDraft.clear();
  },
  { immediate: true },
);
watch(
  () => [route.name, route.query.job, route.query.thread],
  ([name]) => {
    if (String(route.query.job || "") !== retryFocusJob.value) retryFocusJob.value = "";
    ++submissionRequest;
    starting.value = false;
    ++answerRequest;
    activeJob.value = null;
    answerLoading.value = false;
    answerError.value = "";
    stopJobFollowers();
    if (name === "rag") void loadWorkspace(true);
  },
);
// Route hydration can temporarily remove the result region; focus it only once the new attempt is rendered.
watch(
  () => [activeJob.value?.id, answerLoading.value, answerError.value, workspace.value],
  () => {
    if (
      !retryFocusJob.value ||
      activeJob.value?.id !== retryFocusJob.value ||
      String(route.query.job || "") !== retryFocusJob.value ||
      answerLoading.value ||
      answerError.value
    )
      return;
    const region = document.querySelector<HTMLElement>(".research-result-presentation");
    if (region) {
      region.focus();
      retryFocusJob.value = "";
    }
  },
  { flush: "post" },
);
// Account/capability changes invalidate every pending read and visible research artifact.
watch(
  () => [auth.user?.id, auth.user?.role, auth.can("rag.run")],
  () => {
    retryFocusJob.value = "";
    ++submissionRequest;
    starting.value = false;
    ++workspaceRequest;
    ++answerRequest;
    ++runsRequest;
    ++pipelinesRequest;
    activeJob.value = null;
    jobs.value = [];
    sessionJobIds.value = new Set();
    workspace.value = null;
    config.value = null;
    prompt.value = "";
    instructions.value = "";
    answerError.value = "";
    answerLoading.value = false;
    stopJobFollowers();
    researchDraft.clear();
    if (auth.user && auth.can("rag.run") && isNativeResearch.value) void loadWorkspace(true);
  },
);
onMounted(() => {
  if (isNativeResearch.value) void loadWorkspace(true);
});
onBeforeUnmount(() => {
  ++submissionRequest;
  disposed = true;
  ++workspaceRequest;
  ++answerRequest;
  ++runsRequest;
  ++pipelinesRequest;
  stopJobFollowers();
  window.clearTimeout(draftTimer);
  researchDraft.clear();
});
</script>

<template>
  <main class="vue-native-page research-native-page" aria-labelledby="research-page-title">
    <UiPageHeader
      :kicker="i18n.t('research.page_kicker')"
      :title="i18n.t('research.page_title')"
      title-id="research-page-title"
      :description="i18n.t('research.page_subtitle')"
      :actions-label="i18n.t('research.page_state')"
    >
      <template v-if="workspace" #actions>
        <div class="research-page-state">
          <span
            ><i></i
            >{{
              i18n.tf(
                stores.length === 1
                  ? "research.database_count_one"
                  : "research.database_count_other",
                { count: stores.length.toLocaleString(i18n.locale) },
              )
            }}</span
          ><span>{{
            i18n.tf(
              selectedEvidence.length === 1
                ? "research.selected_evidence_count_one"
                : "research.selected_evidence_count_many",
              { count: selectedEvidence.length },
            )
          }}</span>
        </div>
      </template>
    </UiPageHeader>
    <div v-if="workspaceError" class="info error research-workspace-status" role="alert">
      <p>
        <template v-if="workspace">{{ i18n.t("loading.stale") }} </template>{{ workspaceError }}
      </p>
      <button type="button" class="btn" @click="loadWorkspace()">{{ i18n.t("ui.retry") }}</button>
    </div>
    <UiLoadingState
      v-if="loading"
      variant="inline"
      :label="i18n.t(workspace ? 'loading.updating' : 'research.loading_workspace')"
    />

    <AccessibleEmptyState
      v-if="noDatabase"
      icon="database"
      :title="i18n.t('research.empty_state_title')"
      :description="
        canCreateDatabase
          ? i18n.t('research.empty_state_help')
          : i18n.t('research.empty_state_denied')
      "
      :action-label="canCreateDatabase ? i18n.t('research.empty_state_action') : ''"
      @action="openDatabaseCreationFromResearch()"
    />
    <template v-else>
      <button
        v-if="auth.can('rag.run')"
        type="button"
        class="btn"
        :aria-expanded="threadBrowserOpen"
        aria-controls="research-thread-browser"
        @click="threadBrowserOpen = !threadBrowserOpen"
      >
        {{ i18n.t("research.threads_title") }}
      </button>
      <div v-if="auth.can('rag.run') && threadBrowserOpen" id="research-thread-browser">
        <ResearchThreadBrowser
          :thread-id="currentThreadId"
          :job-id="String(route.query.job || '')"
          :retry-disabled="
            starting ||
            loading ||
            Boolean(workspaceError) ||
            !workspace?.can_run ||
            !config ||
            !profiles.length
          "
          :retry-busy="starting"
          :refresh-key="threadRefreshKey"
          @retry-turn="runResearch"
          @select="selectThread"
          @open="openThreadTurn"
          @new="newThread"
          @removed="onThreadRemoved"
        />
      </div>
      <ResearchComposer
        v-model:prompt="prompt"
        v-model:instructions="instructions"
        :source-collection="config?.source_collection || ''"
        :provider-profile-id="config?.provider_profile_id || ''"
        :response-language="config?.response_language || ''"
        :preset="preset"
        :evidence-count="selectedEvidence.length"
        :prompt-metadata="config?.prompt_metadata || normalizedResearchConfig().prompt_metadata"
        :pipeline-name="effectivePipeline?.name || ''"
        :pipeline-version="effectivePipeline?.version || null"
        :pipeline-override="pipelineOverrideActive"
        :stores="stores"
        :profiles="profiles"
        :history="workspace?.history || []"
        :busy="starting"
        :can-run="canRun"
        :can-configure="canConfigureResearch"
        :can-draft="auth.can('rag.run')"
        :can-manage-runs="canManageRuns"
        :disabled-reason="runDisabledReason"
        @update:source-collection="updateConfig({ source_collection: $event })"
        @update:provider-profile-id="changeProfile"
        @update:response-language="updateConfig({ response_language: $event })"
        @update:preset="applyPreset"
        @run="runResearch"
        @settings="settingsDrawer?.open()"
        @pipeline-settings="settingsDrawer?.open('pipeline')"
        @prompt-metadata="settingsDrawer?.open('evidence', true)"
        @runs="runsDrawer?.open()"
        @history="loadHistory"
      />

      <UiLoadingState v-if="runsLoading" variant="inline" :label="i18n.t('loading.updating')" />
      <div v-if="runsError" class="info error research-runs-status" role="alert">
        <p>{{ runsError }}</p>
        <button type="button" class="btn" @click="refreshRuns()">{{ i18n.t("ui.retry") }}</button>
      </div>
      <UiLoadingState
        v-if="pipelinesLoading"
        variant="inline"
        :label="i18n.t('pipelines.loading')"
      />
      <div v-if="pipelinesError" class="info error research-pipelines-status" role="alert">
        <p>{{ pipelinesError }}</p>
        <button type="button" class="btn" @click="loadPipelines()">{{ i18n.t("ui.retry") }}</button>
      </div>
      <ResearchPipelineBar
        :jobs="jobs"
        :selected-job-id="activeJob?.id || ''"
        :can-manage="canManageRuns"
        @select="openJob"
        @cancel="cancelJob"
        @open-runs="runsDrawer?.open()"
      />

      <UiLoadingState
        v-if="answerLoading"
        variant="inline"
        :label="i18n.t('runtime.system_responses_loading')"
      />
      <div v-if="answerError" class="info error research-answer-status" role="alert">
        <p>
          <template v-if="activeResult">{{ i18n.t("loading.stale") }} </template>{{ answerError }}
        </p>
        <button v-if="activeJob" type="button" class="btn" @click="loadAnswer(activeJob)">
          {{ i18n.t("ui.retry") }}
        </button>
      </div>
      <ResearchResultPresentation
        tabindex="-1"
        role="region"
        :aria-label="i18n.t('research.answer')"
        v-if="workspace && ((!answerLoading && !answerError) || activeResult)"
        :job="activeJob"
        :result="activeResult"
        :draft="researchDraft.draft.value"
        :selected-evidence="selectedEvidence"
        :active-evidence-index="activeEvidenceIndex"
        :busy="starting"
        :can-grade="canGrade"
        :can-remove-selected="
          Boolean(workspace?.can_select_evidence) && auth.can('evidence.select')
        "
        :researcher="workspace?.is_researcher || false"
        @copy="copyAnswer"
        @grade="gradeAnswer"
        @rerun="prepareRerun"
        @details="runsDrawer?.open()"
        @evidence="focusEvidence"
        @select-evidence="activeEvidenceIndex = $event"
        @remove-selected="removeEvidence"
        @clear-selected="clearEvidence"
        @open-record="openEvidenceRecord"
        @open-relationships="openEvidenceRelationships"
      />

      <ResearchSettingsDrawer
        v-if="workspace && config"
        ref="settingsDrawer"
        :config="config"
        :profiles="profiles"
        :selected-profile-id="config.provider_profile_id"
        :generation="generation"
        :model="model"
        :models="discoveredModels"
        :metadata-fields="metadataFields"
        :researcher="workspace.is_researcher"
        :pipeline-options="workspace?.pipeline_options || []"
        :pipeline-strategies="workspace?.pipeline_strategies || []"
        :pipeline-assignment="workspace?.pipeline_assignment || null"
        :pipeline-override-allowed="workspace?.pipeline_override_allowed || false"
        :run-pipeline-overrides="runPipelineOverrides"
        @apply="applySettings"
        @discover="discoverModels"
      />
      <ResearchRunsDrawer
        ref="runsDrawer"
        :jobs="jobs"
        :selected-job-id="activeJob?.id || ''"
        :selected-job="activeJob"
        :can-manage="canManageRuns"
        @open="openJob"
        @cancel="cancelJob"
        @remove="removeJob"
        @refresh="refreshRuns"
      />
    </template>
  </main>
</template>

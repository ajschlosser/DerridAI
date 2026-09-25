<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import ResearchComposer from "../components/research/ResearchComposer.vue";
import ResearchResultPresentation from "../components/research/ResearchResultPresentation.vue";
import ResearchSettingsDrawer from "../components/research/ResearchSettingsDrawer.vue";
import ResearchRunsDrawer from "../components/research/ResearchRunsDrawer.vue";
import ResearchPipelineBar from "../components/research/ResearchPipelineBar.vue";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import type {
  ResearchConfig,
  ResearchJob,
  ResearchProfile,
  ResearchWorkspaceSnapshot,
} from "../types/research";
import * as runtime from "../runtime/runtime.js";
import UiPageHeader from "../components/ui/UiPageHeader.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const i18n = useI18nStore();
const isNativeResearch = computed(() => route.name === "rag");
const loading = ref(false);
const noDatabase = ref(false);
const canCreateDatabase = computed(() => auth.can("page.vector"));
const starting = ref(false);
const workspace = ref<ResearchWorkspaceSnapshot | null>(null);
const config = ref<ResearchConfig | null>(null);
const prompt = ref("");
const instructions = ref("");
const preset = ref("balanced");
const model = ref("");
const discoveredModels = ref<string[]>([]);
const generation = ref<Record<string, unknown>>({});
const jobs = ref<ResearchJob[]>([]);
const activeJob = ref<ResearchJob | null>(null);
const sessionJobIds = ref<Set<string>>(new Set());
const activeEvidenceIndex = ref(0);
const settingsDrawer = ref<{ open: () => void } | null>(null);
const runsDrawer = ref<{ open: () => void; close: () => void } | null>(null);
let pollTimer: number | undefined;
let draftTimer: number | undefined;

const selectedEvidence = computed(() => workspace.value?.selected_evidence || []);
const profiles = computed(() => workspace.value?.profiles || []);
const stores = computed(() => workspace.value?.stores || []);
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
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SA-13: preserve legacy setup binding until its owning workflow is extracted.
const resultEvidence = computed(() => activeResult.value?.evidence || []);
const selectedProfile = computed(
  () =>
    profiles.value.find((profile) => profile.id === config.value?.provider_profile_id) ||
    profiles.value[0] ||
    null,
);
const canManageRuns = computed(
  () => Boolean(workspace.value?.can_manage_jobs && auth.can("rag.jobs.own")) || auth.isAdmin,
);
const canConfigureResearch = computed(() =>
  Boolean(workspace.value?.can_run && auth.can("rag.run")),
);
const canGrade = computed(() => auth.isAdmin);
const runDisabledReason = computed(() => {
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
  workspace.value = snapshot;
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
  if (!isNativeResearch.value) return;
  loading.value = true;
  try {
    const snapshot = (await runtime.getResearchWorkspaceSnapshot({
      refresh,
    })) as ResearchWorkspaceSnapshot;
    const requestedJobId = String(route.query.job || "").trim();
    // Explain the missing prerequisite in place; do not toast and bounce the
    // user into an unrelated dialog or away from the page they chose.
    noDatabase.value = !(snapshot.stores || []).length;
    if (noDatabase.value) return;
    hydrate(snapshot, { preserveDraft: Boolean(workspace.value), preserveActive: true });
    if (requestedJobId) {
      activeJob.value = (await runtime.getResearchJob(requestedJobId)) as ResearchJob;
      if (!jobs.value.some((job) => job.id === activeJob.value?.id))
        jobs.value = [activeJob.value, ...jobs.value];
      activeEvidenceIndex.value = 0;
      await nextTick();
      document
        .querySelector(".research-answer-workspace")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (activeJob.value?.status === "completed" && !activeJob.value.result) {
      activeJob.value = (await runtime.getResearchJob(activeJob.value.id)) as ResearchJob;
    }
    schedulePoll();
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  } finally {
    loading.value = false;
  }
}
function persistDraft() {
  if (!config.value) return;
  window.clearTimeout(draftTimer);
  draftTimer = window.setTimeout(
    () => runtime.updateResearchConfig({ prompt: prompt.value, instructions: instructions.value }),
    250,
  );
}
function updateConfig(patch: Partial<ResearchConfig>) {
  if (!config.value) return;
  config.value = { ...config.value, ...patch };
  config.value = runtime.updateResearchConfig(patch) as ResearchConfig;
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
  const common = {
    skip_retrieval: false,
    reranker: "cross_encoder",
    search_types: ["similarity", "lexical", "mmr"],
  };
  if (value === "balanced")
    updateConfig({ ...common, k: 64, fetch_k: 500, lambda_mult: 0.7, rrf_k: 60, rerank_top_n: 24 });
  else if (value === "precision")
    updateConfig({
      ...common,
      k: 40,
      fetch_k: 320,
      lambda_mult: 0.82,
      rrf_k: 60,
      rerank_top_n: 16,
    });
  else if (value === "recall")
    updateConfig({
      ...common,
      k: 96,
      fetch_k: 1000,
      lambda_mult: 0.58,
      rrf_k: 60,
      rerank_top_n: 32,
    });
}
function changeProfile(id: string) {
  updateConfig({ provider_profile_id: id });
  const profile = profiles.value.find((item) => item.id === id) || null;
  model.value = profileModel(profile);
  generation.value = profileGeneration(profile);
  discoveredModels.value = profile?.model ? [String(profile.model)] : [];
}
async function runResearch() {
  if (!config.value || !canRun.value || starting.value) return;
  if (route.query.job) await router.replace({ path: "/rag" });
  starting.value = true;
  try {
    persistDraft();
    const job = (await runtime.startResearchRun({
      prompt: prompt.value,
      instructions: instructions.value,
      provider_profile_id: config.value.provider_profile_id,
      model: model.value,
      generation: generation.value,
      skip_retrieval: preset.value === "evidence" || config.value.skip_retrieval,
      config: { ...config.value, prompt: prompt.value, instructions: instructions.value },
    })) as ResearchJob;
    sessionJobIds.value.add(job.id);
    activeJob.value = job;
    activeEvidenceIndex.value = 0;
    jobs.value = [job, ...jobs.value.filter((item) => item.id !== job.id)];
    schedulePoll(true);
    await nextTick();
    document
      .querySelector(".research-answer-workspace")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  } finally {
    starting.value = false;
  }
}
async function poll() {
  pollTimer = undefined;
  if (!isNativeResearch.value) return;
  try {
    if (canManageRuns.value) {
      const refreshed = (await runtime.refreshResearchJobs()) as ResearchJob[];
      jobs.value = refreshed;
      if (activeJob.value) {
        const summary = refreshed.find((job) => job.id === activeJob.value?.id);
        if (summary) {
          activeJob.value = {
            ...activeJob.value,
            ...summary,
            result: activeJob.value.result || summary.result,
          };
          if (["completed", "failed", "cancelled"].includes(summary.status))
            activeJob.value = (await runtime.getResearchJob(summary.id)) as ResearchJob;
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
          activeSessionJobs.map((job) => runtime.getResearchJob(job.id) as Promise<ResearchJob>),
        );
        const byId = new Map(refreshed.map((job) => [job.id, job]));
        jobs.value = jobs.value.map((job) => byId.get(job.id) || job);
        if (activeJob.value && byId.has(activeJob.value.id))
          activeJob.value = byId.get(activeJob.value.id) || activeJob.value;
      }
    }
  } catch (error) {
    console.warn("Research polling failed", error);
  }
  schedulePoll();
}
function schedulePoll(force = false) {
  window.clearTimeout(pollTimer);
  const active =
    Boolean(
      activeJob.value && ["queued", "running", "cancelling"].includes(activeJob.value.status),
    ) || jobs.value.some((job) => ["queued", "running", "cancelling"].includes(job.status));
  if ((force || active) && isNativeResearch.value) pollTimer = window.setTimeout(poll, 3000);
}
async function openJob(job: ResearchJob) {
  try {
    if (route.query.job) await router.replace({ path: "/rag" });
    activeJob.value =
      job.status === "completed" ? ((await runtime.getResearchJob(job.id)) as ResearchJob) : job;
    activeEvidenceIndex.value = 0;
    runsDrawer.value?.close();
    await nextTick();
    document
      .querySelector(".research-answer-workspace")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function cancelJob(job: ResearchJob) {
  try {
    const updated = (await runtime.cancelResearchJob(job.id)) as ResearchJob;
    if (activeJob.value?.id === job.id) activeJob.value = updated;
    await refreshRuns();
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function removeJob(job: ResearchJob) {
  if (!window.confirm(i18n.t("research.remove_run_confirm"))) return;
  try {
    await runtime.deleteResearchJob(job.id);
    if (activeJob.value?.id === job.id) activeJob.value = null;
    await refreshRuns();
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function refreshRuns() {
  jobs.value = (await runtime.refreshResearchJobs()) as ResearchJob[];
  schedulePoll();
}
function loadHistory(item: Record<string, unknown>) {
  prompt.value = String(item.prompt || "");
  instructions.value = String(item.instructions || "");
  persistDraft();
  runtime.notifyToast(i18n.t("research.question_restored"), {
    tone: "success",
  });
}
function removeEvidence(key: string) {
  try {
    const evidence = runtime.removeResearchEvidence(key);
    if (workspace.value) workspace.value = { ...workspace.value, selected_evidence: evidence };
    if (!evidence.length && preset.value === "evidence") applyPreset("balanced");
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
function clearEvidence() {
  try {
    runtime.clearResearchEvidence();
    if (workspace.value) workspace.value = { ...workspace.value, selected_evidence: [] };
    if (config.value) config.value = { ...config.value, skip_retrieval: false };
    if (preset.value === "evidence") preset.value = "balanced";
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
async function copyAnswer() {
  try {
    await navigator.clipboard.writeText(activeResult.value?.answer || "");
    runtime.notifyToast(i18n.t("research.answer_copied"), { tone: "success" });
  } catch {
    runtime.notifyToast(i18n.t("research.clipboard_failed"), {
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
    await runtime.gradeResearchJob(activeJob.value.id);
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
function prepareRerun() {
  if (!activeJob.value) return;
  if (route.query.job) void router.replace({ path: "/rag" });
  const next = runtime.prepareResearchRerun(activeJob.value) as ResearchConfig;
  config.value = { ...next };
  prompt.value = next.prompt || "";
  instructions.value = next.instructions || "";
  preset.value = inferPreset(next);
  const profile =
    profiles.value.find((item) => item.id === next.provider_profile_id) || selectedProfile.value;
  model.value = profileModel(profile || null);
  generation.value = profileGeneration(profile || null);
  activeJob.value = null;
  runtime.notifyToast(i18n.t("research.rerun_loaded"), {
    tone: "success",
  });
  void nextTick(() => document.querySelector<HTMLTextAreaElement>("#researchQuestion")?.focus());
}
async function discoverModels() {
  if (!config.value) return;
  try {
    discoveredModels.value = (await runtime.discoverResearchModels(
      config.value.provider_profile_id,
    )) as string[];
    runtime.notifyToast(`${discoveredModels.value.length} ${i18n.t("research.models_found")}`, {
      tone: "success",
    });
  } catch (error) {
    runtime.notifyToast(error instanceof Error ? error.message : String(error), { tone: "danger" });
  }
}
function applySettings(payload: {
  config: Partial<ResearchConfig>;
  generation: Record<string, unknown>;
  model: string;
}) {
  updateConfig(payload.config);
  generation.value = { ...payload.generation };
  model.value = payload.model || profileModel(selectedProfile.value);
  preset.value = "custom";
  runtime.notifyToast(i18n.t("research.settings_applied"), {
    tone: "success",
  });
}

watch(prompt, persistDraft);
watch(instructions, persistDraft);
watch(
  () => [route.name, route.query.job],
  ([name]) => {
    window.clearTimeout(pollTimer);
    if (name === "rag") void loadWorkspace(true);
  },
);
onMounted(() => {
  if (isNativeResearch.value) void loadWorkspace(true);
});
onBeforeUnmount(() => {
  window.clearTimeout(pollTimer);
  window.clearTimeout(draftTimer);
});
</script>

<template>
  <main class="vue-native-page research-native-page" aria-labelledby="research-page-title">
    <div v-if="loading && !workspace" class="research-loading" role="status">
      <span class="spinner"></span>{{ i18n.t("research.loading_workspace") }}
    </div>
    <AccessibleEmptyState
      v-else-if="noDatabase"
      icon="database"
      :title="i18n.t('research.empty_state_title')"
      :description="
        canCreateDatabase
          ? i18n.t('research.empty_state_help')
          : i18n.t('research.empty_state_denied')
      "
      :action-label="canCreateDatabase ? i18n.t('research.empty_state_action') : ''"
      @action="runtime.openDatabaseCreationFromResearch?.()"
    />
    <template v-else-if="workspace && config">
      <UiPageHeader
        :kicker="i18n.t('research.page_kicker')"
        :title="i18n.t('research.page_title')"
        title-id="research-page-title"
        :description="i18n.t('research.page_subtitle')"
        :actions-label="i18n.t('research.page_state')"
      >
        <template #actions>
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

      <ResearchComposer
        v-model:prompt="prompt"
        v-model:instructions="instructions"
        :source-collection="config.source_collection"
        :provider-profile-id="config.provider_profile_id"
        :response-language="config.response_language"
        :preset="preset"
        :evidence-count="selectedEvidence.length"
        :stores="stores"
        :profiles="profiles"
        :history="workspace.history || []"
        :busy="starting"
        :can-run="canRun"
        :can-configure="canConfigureResearch"
        :can-manage-runs="canManageRuns"
        :disabled-reason="runDisabledReason"
        @update:source-collection="updateConfig({ source_collection: $event })"
        @update:provider-profile-id="changeProfile"
        @update:response-language="updateConfig({ response_language: $event })"
        @update:preset="applyPreset"
        @run="runResearch"
        @settings="settingsDrawer?.open()"
        @runs="runsDrawer?.open()"
        @history="loadHistory"
      />

      <ResearchPipelineBar
        :jobs="jobs"
        :selected-job-id="activeJob?.id || ''"
        :can-manage="canManageRuns"
        @select="openJob"
        @cancel="cancelJob"
        @open-runs="runsDrawer?.open()"
      />

      <ResearchResultPresentation
        :job="activeJob"
        :result="activeResult"
        :selected-evidence="selectedEvidence"
        :active-evidence-index="activeEvidenceIndex"
        :busy="starting"
        :can-grade="canGrade"
        :can-remove-selected="workspace.can_select_evidence && auth.can('evidence.select')"
        :researcher="workspace.is_researcher"
        @copy="copyAnswer"
        @grade="gradeAnswer"
        @rerun="prepareRerun"
        @details="runsDrawer?.open()"
        @evidence="focusEvidence"
        @select-evidence="activeEvidenceIndex = $event"
        @remove-selected="removeEvidence"
        @clear-selected="clearEvidence"
      />

      <ResearchSettingsDrawer
        ref="settingsDrawer"
        :config="config"
        :profiles="profiles"
        :selected-profile-id="config.provider_profile_id"
        :generation="generation"
        :model="model"
        :models="discoveredModels"
        :metadata-fields="metadataFields"
        :researcher="workspace.is_researcher"
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

<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import type { PublicationRecord, ResearchResponse, ResearchWarning } from "../sdk/src/types";
import UiButton from "../src/components/ui/UiButton.vue";
import UiTextarea from "../src/components/ui/UiTextarea.vue";
import PublishedIndexStatus from "./PublishedIndexStatus.vue";
import PublishedMethodStrip from "./PublishedMethodStrip.vue";
import PublishedResearchConfig from "./PublishedResearchConfig.vue";
import PublishedResearchResult from "./PublishedResearchResult.vue";
import { type PublishedResearchSettings, usePublishedSite } from "./siteContext";

const site = usePublishedSite();
const question = ref("");
const running = ref(false);
const status = ref("");
const statusTone = ref<"" | "success" | "warning" | "error">("");
const evidenceTarget = ref<HTMLElement | null>(null);
const response = ref<ResearchResponse | null>(null);
const recordsById = ref(new Map<string, PublicationRecord>());

function cloneResearchSettings(value: PublishedResearchSettings): PublishedResearchSettings {
  return { ...value, works: [...value.works] };
}

const runSettings = ref(cloneResearchSettings(site.researchDefaults.value));
const progressStage = ref(0);
const elapsedSeconds = ref(0);
let elapsedTimer: number | undefined;

const progressSummary = computed(() =>
  site.t("site.runtime.research_progress_summary", {
    current: progressStage.value,
    total: 3,
    seconds: elapsedSeconds.value,
  }),
);

const methods = ref({
  text: true,
  vector: site.semanticReady(),
  llm: Boolean(site.capabilities.value?.provider?.generation),
});

const localIndexVisible = computed(
  () =>
    Boolean(site.capabilities.value?.localIndex) &&
    !site.capabilities.value?.localIndex?.usesPublishedVectors,
);

const answerText = computed(() =>
  response.value?.answer
    ? String(response.value.answer)
    : response.value?.evidencePacket?.evidence?.length
      ? site.t("site.runtime.generation_unavailable_evidence")
      : "",
);

function resolvedMode(settings: PublishedResearchSettings) {
  return settings.mode === "auto"
    ? site.semanticReady()
      ? "hybrid"
      : "keyword"
    : settings.mode;
}

function startElapsedTimer() {
  stopElapsedTimer();
  elapsedSeconds.value = 0;
  elapsedTimer = window.setInterval(() => {
    elapsedSeconds.value += 1;
  }, 1000);
}

function stopElapsedTimer() {
  if (elapsedTimer !== undefined) {
    window.clearInterval(elapsedTimer);
    elapsedTimer = undefined;
  }
}

function resetRunSettings() {
  runSettings.value = cloneResearchSettings(site.researchDefaults.value);
}

onBeforeUnmount(stopElapsedTimer);

async function openEvidenceRecord(recordId: string) {
  const known = recordsById.value.get(String(recordId));
  const record = known || (await site.client.value?.records.get(recordId));
  if (record) site.openRecord(record);
}

async function runResearch() {
  const q = question.value.trim();
  if (!q || !site.client.value) return;
  const config = site.normalizeResearchSettings(runSettings.value);
  runSettings.value = cloneResearchSettings(config);
  const mode = resolvedMode(config);

  running.value = true;
  response.value = null;
  recordsById.value = new Map();
  progressStage.value = 1;
  startElapsedTimer();
  methods.value = {
    text: mode !== "semantic",
    vector: mode !== "keyword",
    llm: Boolean(site.capabilities.value?.provider?.generation),
  };
  statusTone.value = "";
  status.value = site.t("site.runtime.activity_research_retrieving");

  const stopProgress = site.subscribeResearchProgress(({ message, stage }) => {
    status.value = message;
    progressStage.value = stage;
  });

  try {
    const result = await site.client.value.research({
      question: q,
      retrieval: {
        mode,
        limit: config.k,
        fetchLimit: config.fetchK,
        evidenceLimit: config.topN,
        mmrLambda: config.mmrLambda,
        filters: config.works.length ? { work: config.works } : undefined,
      },
    });
    recordsById.value = new Map(
      (result.retrieval.results || []).map((item) => [
        String(item.record?.record_id || ""),
        item.record,
      ]),
    );
    response.value = result;
    methods.value = {
      text: result.retrieval.modeUsed !== "semantic",
      vector: result.retrieval.modeUsed !== "keyword",
      llm: Boolean(result.generation),
    };
    const retrievalWarning = site.warningText(result.retrieval.warnings);
    const generationWarning = result.warnings.some(
      (warning: ResearchWarning) => warning.code === "generation_unavailable",
    );

    if (result.answer) {
      statusTone.value = retrievalWarning ? "warning" : "success";
      status.value = retrievalWarning
        ? site.t("site.runtime.complete_with_warning", { warning: retrievalWarning })
        : site.t("site.runtime.complete");
    } else if (result.evidencePacket.evidence.length) {
      statusTone.value = "warning";
      status.value = generationWarning
        ? site.t("site.runtime.sdk_generation_unavailable")
        : site.t("site.runtime.complete");
    } else {
      statusTone.value = "warning";
      status.value = site.t("site.runtime.no_evidence");
    }
  } catch (error) {
    statusTone.value = "error";
    status.value = site.t("site.runtime.research_failed", {
      error: error instanceof Error ? error.message : String(error),
    });
  } finally {
    stopProgress();
    stopElapsedTimer();
    running.value = false;
  }
}
</script>

<template>
  <div class="research-layout">
    <section class="panel stack" data-tour="research" aria-labelledby="research-heading">
      <h2 id="research-heading">{{ site.t("site.runtime.research") }}</h2>
      <PublishedMethodStrip :text="methods.text" :vector="methods.vector" :llm="methods.llm" />
      <UiTextarea
        v-model="question"
        class="control"
        :placeholder="site.t('site.runtime.question_placeholder')"
        :aria-label="site.t('site.runtime.question')"
      />
      <details class="research-run-settings">
        <summary>{{ site.t("site.runtime.research_run_settings") }}</summary>
        <div class="research-run-settings-body">
          <p class="muted">{{ site.t("site.runtime.research_run_settings_help") }}</p>
          <PublishedResearchConfig
            v-model="runSettings"
            id-prefix="published-research-run"
            :disabled="running"
          />
          <UiButton
            :label="site.t('site.runtime.research_reset_to_defaults')"
            :disabled="running"
            @click="resetRunSettings"
          />
        </div>
      </details>
      <UiButton
        variant="primary"
        :label="site.t('site.runtime.ask')"
        :disabled="running"
        @click="runResearch"
      />
      <div v-if="running" class="research-run-progress">
        <progress :aria-label="status"></progress>
        <div class="meta" aria-hidden="true">{{ progressSummary }}</div>
      </div>
      <div
        class="status"
        :class="statusTone"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {{ status }}
      </div>
      <PublishedIndexStatus
        v-if="localIndexVisible"
        initial-build-label-key="site.runtime.index_build_browser"
      />
      <div class="answer" aria-live="polite">
        <PublishedResearchResult
          v-if="
            response && evidenceTarget && (answerText || response.evidencePacket.evidence.length)
          "
          :answer="answerText"
          :evidence="response.evidencePacket.evidence"
          :records-by-id="recordsById"
          :evidence-target="evidenceTarget"
          :evidence-label="site.t('site.runtime.evidence')"
          :open-record-label="site.t('site.runtime.view_record')"
          :on-open-record="openEvidenceRecord"
        />
      </div>
    </section>

    <aside class="stack research-evidence-pane" :aria-label="site.t('site.runtime.research_tools')">
      <section
        ref="evidenceTarget"
        class="research-evidence-panel"
        data-tour="evidence"
        role="region"
        :aria-label="site.t('site.runtime.evidence')"
      ></section>
    </aside>
  </div>
</template>

<style scoped>
.research-run-settings {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}
.research-run-settings > summary {
  min-height: var(--control-height);
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  font-weight: var(--fw-bold);
}
.research-run-settings > summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.research-run-settings-body {
  display: grid;
  gap: var(--space-4);
  padding: 0 var(--space-4) var(--space-4);
}
.research-run-settings-body > p {
  margin: 0;
}
.research-run-progress {
  display: grid;
  gap: var(--space-2);
}
.research-run-progress progress {
  width: 100%;
}
</style>

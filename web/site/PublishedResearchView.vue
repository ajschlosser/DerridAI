<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, ref } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import UiTextarea from "../src/components/ui/UiTextarea.vue";
import PublishedIndexStatus from "./PublishedIndexStatus.vue";
import PublishedMethodStrip from "./PublishedMethodStrip.vue";
import PublishedResearchResult from "./PublishedResearchResult.vue";
import { usePublishedSite } from "./siteContext";

const site = usePublishedSite();
const question = ref("");
const running = ref(false);
const status = ref("");
const statusTone = ref<"" | "success" | "warning" | "error">("");
const evidenceTarget = ref<HTMLElement | null>(null);
const response = ref<any | null>(null);
const recordsById = ref(new Map<string, any>());
const methods = ref({
  text: true,
  vector: site.semanticReady(),
  llm: Boolean(site.capabilities.value?.provider?.generation),
});

const localIndexVisible = computed(
  () =>
    Boolean(site.capabilities.value?.localIndex) &&
    !Boolean(site.capabilities.value?.localIndex?.usesPublishedVectors),
);

const answerText = computed(() =>
  response.value?.answer
    ? String(response.value.answer)
    : response.value?.evidencePacket?.evidence?.length
      ? site.t("site.runtime.generation_unavailable_evidence")
      : "",
);

async function openEvidenceRecord(recordId: string) {
  const known = recordsById.value.get(String(recordId));
  const record = known || (await site.client.value?.records.get(recordId));
  if (record) site.openRecord(record);
}

async function runResearch() {
  const q = question.value.trim();
  if (!q || !site.client.value) return;
  running.value = true;
  response.value = null;
  recordsById.value = new Map();
  methods.value = {
    text: true,
    vector: site.semanticReady(),
    llm: Boolean(site.capabilities.value?.provider?.generation),
  };
  statusTone.value = "";
  status.value = site.semanticReady()
    ? site.t("site.runtime.activity_research_hybrid")
    : site.t("site.runtime.activity_research_text");

  const stopProgress = site.subscribeProgress((message) => {
    status.value = message;
  });

  try {
    const result = await site.client.value.research({
      question: q,
      retrieval: {
        mode: site.semanticReady() ? "hybrid" : "keyword",
        limit: 24,
        evidenceLimit: 10,
        mmrLambda: 0.72,
      },
    });
    recordsById.value = new Map(
      (result.retrieval.results || []).map((item: any) => [
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
      (warning: any) => warning.code === "generation_unavailable",
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
    running.value = false;
  }
}
</script>

<template>
  <div class="research-layout">
    <section
      class="panel stack"
      data-tour="research"
      aria-labelledby="research-heading"
    >
      <h2 id="research-heading">{{ site.t("site.runtime.research") }}</h2>
      <PublishedMethodStrip
        :text="methods.text"
        :vector="methods.vector"
        :llm="methods.llm"
      />
      <UiTextarea
        v-model="question"
        class="control"
        :placeholder="site.t('site.runtime.question_placeholder')"
        :aria-label="site.t('site.runtime.question')"
      />
      <UiButton
        variant="primary"
        :label="site.t('site.runtime.ask')"
        :disabled="running"
        @click="runResearch"
      />
      <div
        class="status"
        :class="statusTone"
        role="status"
        aria-live="polite"
      >
        {{ status }}
      </div>
      <PublishedIndexStatus
        v-if="localIndexVisible"
        initial-build-label-key="site.runtime.index_build_browser"
      />
      <div class="answer" aria-live="polite">
        <PublishedResearchResult
          v-if="response && evidenceTarget && (answerText || response.evidencePacket.evidence.length)"
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

    <aside
      class="stack research-evidence-pane"
      :aria-label="site.t('site.runtime.research_tools')"
    >
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

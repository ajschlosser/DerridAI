<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import type { ProviderProfile } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import { openBuildWarnings } from "../../features/corpus-builder/domain/buildWarnings";
import UiButton from "../ui/UiButton.vue";
import UiNoticeStack, { type Notice } from "../ui/UiNoticeStack.vue";
import CorpusRunDiagnostics from "./CorpusRunDiagnostics.vue";

const props = defineProps<{
  build: CorpusBuild;
  profiles: ProviderProfile[];
  activeProfileId?: string;
  activeModel?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{
  switchProfile: [profileId: string, model: string];
  settle: [];
  cancel: [];
  resume: [];
  runAnother: [];
  openRecord: [recordId: string];
  inspectEditorialMemory: [];
  /** Record that these warnings were seen; they stay in the build's provenance. */
  acknowledgeWarnings: [warnings: string[]];
}>();
const i18n = useI18nStore();
const expanded = ref(false);
const buildRunning = computed(() =>
  ["queued", "running"].includes(String(props.build.status || "")),
);
const operationRunning = computed(() =>
  ["queued", "running"].includes(String(props.build.metadata_operation?.state || "")),
);
const active = computed(() => buildRunning.value || operationRunning.value);
const canResume = computed(
  () =>
    Boolean(props.build.resumable) &&
    !buildRunning.value &&
    ["failed", "interrupted", "cancelled", "blocked"].includes(String(props.build.status || "")),
);
const percent = computed(() => {
  const op = props.build.metadata_operation;
  if (!buildRunning.value && operationRunning.value && op?.records_total) {
    return Math.round((Number(op.records_processed || 0) / Number(op.records_total)) * 100);
  }
  return Math.max(0, Math.min(100, Math.round(Number(props.build.progress || 0) * 100)));
});
const warningNotices = computed<Notice[]>(() =>
  openBuildWarnings(props.build).map((text) => ({ id: text, tone: "warning", text })),
);
// A build error is state, not history: closing it hides it until the build reports a different one.
const dismissedError = ref("");
const errorNotices = computed<Notice[]>(() =>
  props.build.error && props.build.error !== dismissedError.value
    ? [{ id: "build-error", tone: "error", text: String(props.build.error) }]
    : [],
);
const attention = computed(() => errorNotices.value.length + warningNotices.value.length > 0);
const engaged = computed(() => active.value || attention.value || canResume.value);
const model = computed(() => props.activeModel || props.build.model || "");
const label = computed(() => {
  if (!active.value) return i18n.t("pdf_corpus.review_run.details");
  const stage = operationRunning.value && !buildRunning.value ? "enriching" : props.build.stage;
  return [
    i18n.t(`pdf_corpus.review_run.${stage === "enriching" ? "enriching" : "running"}`),
    `${percent.value}%`,
    model.value,
  ]
    .filter(Boolean)
    .join(" · ");
});
</script>

<template>
  <div class="review-run-status">
    <UiButton
      v-if="!engaged"
      size="small"
      :label="i18n.t('pdf_corpus.review_run.run_another')"
      :disabled="disabled"
      @click="emit('runAnother')"
    />
    <template v-else>
      <span class="review-run-controls">
        <UiButton size="small" :expanded="expanded" :label="label" @click="expanded = !expanded" />
        <UiButton
          v-if="canResume"
          size="small"
          :label="i18n.t('pdf_corpus.resume')"
          :disabled="disabled"
          @click="emit('resume')"
        />
        <span v-if="active" class="sr-only" role="status">{{ label }}</span>
      </span>
      <div v-if="attention" class="review-run-alerts">
        <UiNoticeStack
          :items="errorNotices"
          :label="i18n.t('pdf_corpus.build_error')"
          @dismiss="dismissedError = String(build.error || '')"
        />
        <UiNoticeStack
          :items="warningNotices"
          :label="i18n.t('pdf_corpus.build_warnings_label')"
          mode="acknowledge"
          :limit="3"
          :disabled="disabled"
          @dismiss="(id) => emit('acknowledgeWarnings', [id])"
          @dismiss-all="(ids) => emit('acknowledgeWarnings', ids)"
        />
      </div>
      <div v-if="expanded" class="review-run-detail">
        <CorpusRunDiagnostics
          :build="build"
          :profiles="profiles"
          :active-profile-id="activeProfileId"
          :active-model="activeModel"
          :disabled="disabled"
          @switch-profile="(profileId, model) => emit('switchProfile', profileId, model)"
          @settle="emit('settle')"
          @cancel="emit('cancel')"
          @run-another="emit('runAnother')"
          @open-record="(recordId) => emit('openRecord', recordId)"
          @inspect-editorial-memory="emit('inspectEditorialMemory')"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
/* The parent header lays out the pieces; the alerts and detail wrap onto their own rows. */
.review-run-status {
  display: contents;
}
.review-run-controls {
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
}
.review-run-alerts,
.review-run-detail {
  flex: 1 1 100%;
  min-width: 0;
}
.review-run-detail {
  max-height: 40vh;
  overflow: auto;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
</style>

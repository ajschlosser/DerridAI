<script setup lang="ts">
import { computed, ref } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import type { ProviderProfile } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import CorpusProviderSwitcher from "../CorpusProviderSwitcher.vue";
import CorpusMetadataLiveStatus from "../CorpusMetadataLiveStatus.vue";
import CorpusEnrichmentPassStatus from "../CorpusEnrichmentPassStatus.vue";
import CorpusHandsFreeReport from "../CorpusHandsFreeReport.vue";
import CorpusEnrichmentMetrics from "../CorpusEnrichmentMetrics.vue";
import CorpusTextCleanupSummary from "../CorpusTextCleanupSummary.vue";
import CorpusLlmEffectivenessPanel from "../CorpusLlmEffectivenessPanel.vue";
import UiButton from "../ui/UiButton.vue";
import UiNoticeStack, { type Notice } from "../ui/UiNoticeStack.vue";
import { openBuildWarnings } from "../../features/corpus-builder/domain/buildWarnings";

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
const running = computed(() => ["queued", "running"].includes(String(props.build.status || "")));
const canResume = computed(
  () =>
    Boolean(props.build.resumable) &&
    !running.value &&
    ["failed", "interrupted", "cancelled", "blocked"].includes(String(props.build.status || "")),
);
const progress = computed(() =>
  Math.max(0, Math.min(100, Math.round(Number(props.build.progress || 0) * 100))),
);
// Open warnings are the ones nobody has acknowledged; acknowledged ones stay with the build (technical details).
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
const operation = computed(() => props.build.metadata_operation || {});
const operationState = computed(() => String(operation.value.state || ""));
const contribution = computed(() => props.build.llm_contribution || {});
</script>

<template>
  <section class="run-monitor" aria-labelledby="corpus-run-monitor-title">
    <header class="run-monitor-head">
      <div class="run-monitor-identity">
        <span class="eyebrow">{{ i18n.t("pdf_corpus.run_monitor", "Run monitor") }}</span>
        <h3 id="corpus-run-monitor-title">
          {{ i18n.t(`pdf_corpus.stage.${build.stage}`, build.stage || build.status) }}
        </h3>
        <p>
          <span>{{ activeProfileId || build.provider || "—" }}</span>
          <span aria-hidden="true"> · </span>
          <span>{{ activeModel || build.model || "—" }}</span>
          <template v-if="operationState">
            <span aria-hidden="true"> · </span>
            <span>{{ operationState.replaceAll("_", " ") }}</span>
          </template>
        </p>
      </div>
      <div class="run-monitor-state">
        <strong>{{ progress }}%</strong>
        <span v-if="running">{{ i18n.t("pdf_corpus.running", "Running") }}</span>
        <span v-else>{{ i18n.t(`pdf_corpus.status.${build.status}`, build.status) }}</span>
        <UiButton
          v-if="canResume"
          size="small"
          :label="i18n.t('pdf_corpus.resume')"
          :disabled="disabled"
          @click="emit('resume')"
        />
        <UiButton
          size="small"
          :expanded="expanded"
          :label="
            expanded
              ? i18n.t('pdf_corpus.hide_diagnostics', 'Hide diagnostics')
              : i18n.t('pdf_corpus.show_diagnostics', 'Show diagnostics')
          "
          @click="expanded = !expanded"
        />
      </div>
    </header>

    <progress
      class="run-monitor-progress"
      max="100"
      :value="progress"
      :aria-label="i18n.t('pdf_corpus.progress')"
    ></progress>

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

    <CorpusMetadataLiveStatus
      v-if="running && build.stage === 'enriching'"
      :build="build"
      :disabled="disabled"
      @settle="emit('settle')"
      @cancel="emit('cancel')"
    />
    <CorpusEnrichmentPassStatus
      :build="build"
      :disabled="disabled"
      @stop="emit('cancel')"
      @run-another="emit('runAnother')"
    />
    <CorpusHandsFreeReport
      :report="build.autonomous_report"
      @open-record="emit('openRecord', $event)"
    />

    <div v-if="expanded" class="run-monitor-diagnostics">
      <CorpusProviderSwitcher
        v-if="profiles.length"
        :profiles="profiles"
        :active-profile-id="activeProfileId || ''"
        :active-model="activeModel || ''"
        :history="build.provider_profile_history || []"
        :disabled="disabled || !running"
        @change="(profileId, model) => emit('switchProfile', profileId, model)"
      />
      <CorpusEnrichmentMetrics :build-id="build.build_id" />
      <CorpusTextCleanupSummary v-if="build.text_cleanup" :summary="build.text_cleanup" />
      <CorpusLlmEffectivenessPanel
        v-if="build.llm_contribution"
        :contribution="contribution"
        :family-effectiveness="build.llm_family_effectiveness || {}"
        :confidence-calibration="build.llm_confidence_calibration || {}"
        :model-effectiveness="build.llm_model_effectiveness || {}"
        :editorial-examples-used="Number(build.llm_metrics?.editorial_examples_used || 0)"
        @inspect-editorial-memory="emit('inspectEditorialMemory')"
      />
    </div>
  </section>
</template>

<style scoped>
.run-monitor {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}
.run-monitor-head {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
  justify-content: space-between;
}
.run-monitor-identity {
  min-width: 0;
}
.run-monitor-identity h3 {
  margin: var(--space-1) 0;
  font-size: var(--fs-base);
}
.run-monitor-identity p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.run-monitor-state {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  font-size: var(--fs-sm);
}
.run-monitor-progress {
  width: 100%;
  height: 6px;
}
.run-monitor-diagnostics {
  display: grid;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.eyebrow {
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-secondary);
  font-weight: var(--fw-bold);
}
@media (max-width: 720px) {
  .run-monitor-head {
    display: grid;
  }
  .run-monitor-state {
    justify-content: flex-start;
  }
}
</style>

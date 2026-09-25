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
  runAnother: [];
  openRecord: [recordId: string];
  inspectEditorialMemory: [];
}>();
const i18n = useI18nStore();
const expanded = ref(false);
const running = computed(() => ["queued", "running"].includes(String(props.build.status || "")));
const progress = computed(() =>
  Math.max(0, Math.min(100, Math.round(Number(props.build.progress || 0) * 100))),
);
const warnings = computed(() => props.build.warnings || []);
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
        <button
          type="button"
          class="btn small"
          :aria-expanded="expanded"
          @click="expanded = !expanded"
        >
          {{
            expanded
              ? i18n.t("pdf_corpus.hide_diagnostics", "Hide diagnostics")
              : i18n.t("pdf_corpus.show_diagnostics", "Show diagnostics")
          }}
        </button>
      </div>
    </header>

    <progress
      class="run-monitor-progress"
      max="100"
      :value="progress"
      :aria-label="i18n.t('pdf_corpus.progress')"
    ></progress>

    <div v-if="build.error || warnings.length" class="run-monitor-alerts" role="status">
      <p v-if="build.error">{{ build.error }}</p>
      <ul v-if="warnings.length">
        <li v-for="warning in warnings.slice(0, 5)" :key="warning">{{ warning }}</li>
      </ul>
    </div>

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
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.run-monitor-head {
  display: flex;
  gap: 18px;
  align-items: flex-start;
  justify-content: space-between;
}
.run-monitor-identity {
  min-width: 0;
}
.run-monitor-identity h3 {
  margin: 2px 0 3px;
  font-size: 0.9375rem;
}
.run-monitor-identity p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.run-monitor-state {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  font-size: 0.8125rem;
}
.run-monitor-progress {
  width: 100%;
  height: 6px;
}
.run-monitor-alerts {
  padding: 8px 10px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 8px;
  background: var(--tone-warn-bg);
  font-size: 0.8125rem;
}
.run-monitor-alerts p,
.run-monitor-alerts ul {
  margin: 0;
}
.run-monitor-alerts ul {
  padding-inline-start: 18px;
}
.run-monitor-diagnostics {
  display: grid;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.eyebrow {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 800;
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

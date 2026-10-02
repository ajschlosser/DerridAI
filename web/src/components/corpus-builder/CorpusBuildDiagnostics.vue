<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, reactive } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import CorpusBuildTelemetry from "../CorpusBuildTelemetry.vue";
import CorpusBuildTimeline from "../CorpusBuildTimeline.vue";
import CorpusDocumentIntelligenceStatus from "../CorpusDocumentIntelligenceStatus.vue";
import CorpusLlmActivityInspector from "../CorpusLlmActivityInspector.vue";
import CorpusModelActivity from "../CorpusModelActivity.vue";
import CorpusQualitySummary from "../CorpusQualitySummary.vue";

interface GuidanceItem {
  field: string;
  label: string;
  instructions: string;
  lookFor: string[];
}

const props = defineProps<{
  build: CorpusBuild;
  modelLabel?: string;
  runGuidance?: GuidanceItem[];
  summaryLabel?: string;
  summaryHelp?: string;
}>();
const i18n = useI18nStore();
// Diagnostics are for auditing, so nothing inside is mounted until its section is opened.
const opened = reactive({
  root: false,
  quality: false,
  model: false,
  intelligence: false,
  manifest: false,
  timeline: false,
});
type SectionId = keyof typeof opened;
function track(id: SectionId, event: Event) {
  opened[id] = (event.target as HTMLDetailsElement).open;
}
const segmentation = computed(() => ({
  candidateCount: props.build.boundary_candidate_count || 0,
  deterministicSplits: props.build.boundary_deterministic_split_count || 0,
  deterministicKeeps: props.build.boundary_deterministic_keep_count || 0,
  llmAdjudications: props.build.boundary_llm_adjudication_count || 0,
  llmBatchCalls: props.build.boundary_llm_batch_call_count || 0,
  llmSplits: props.build.boundary_llm_split_count || 0,
  llmKeeps: props.build.boundary_llm_keep_count || 0,
  provisionalSplits: props.build.provisional_boundary_count || 0,
  sizeOptimizedSplits: props.build.size_optimized_boundary_count || 0,
  absoluteSafetySplits: props.build.absolute_safety_boundary_count || 0,
  budgetSkipped: props.build.boundary_budget_skipped_count || 0,
  classifierFailures: props.build.boundary_classifier_failure_count || 0,
  reviewCount: props.build.boundary_review_count || 0,
}));
const unresolved = computed(
  () =>
    props.build.boundary_review_count || props.build.segmentation_unresolved_regions?.length || 0,
);
</script>

<template>
  <details
    class="corpus-build-diagnostics"
    :aria-label="summaryLabel || i18n.t('pdf_corpus.diagnostics.title')"
    @toggle="track('root', $event)"
  >
    <summary>
      <span>{{ summaryLabel || i18n.t("pdf_corpus.diagnostics.title") }}</span>
      <small>{{ summaryHelp || i18n.t("pdf_corpus.diagnostics.help") }}</small>
    </summary>
    <div v-if="opened.root" class="diagnostics-body">
      <slot name="activity"></slot>
      <details class="diagnostics-section" @toggle="track('quality', $event)">
        <summary>{{ i18n.t("pdf_corpus.diagnostics.quality") }}</summary>
        <div v-if="opened.quality" class="diagnostics-content">
          <CorpusQualitySummary :build="build" />
          <CorpusBuildTelemetry
            :stage="build.publication ? 'published' : build.stage"
            :validation="build.validation || null"
            :llm-metrics="build.llm_metrics || null"
            :metadata-operation="build.metadata_operation || null"
            :unresolved-count="unresolved"
            :segmentation-telemetry="segmentation"
          />
        </div>
      </details>

      <details class="diagnostics-section" @toggle="track('model', $event)">
        <summary>{{ i18n.t("pdf_corpus.diagnostics.model_activity") }}</summary>
        <div v-if="opened.model" class="diagnostics-content">
          <CorpusModelActivity :activity="build.llm_activity" />
          <CorpusLlmActivityInspector :build-id="build.build_id" />
        </div>
      </details>

      <details
        v-if="build.document_intelligence || build.linguistic_annotations"
        class="diagnostics-section"
        @toggle="track('intelligence', $event)"
      >
        <summary>{{ i18n.t("pdf_corpus.diagnostics.document_intelligence") }}</summary>
        <div v-if="opened.intelligence" class="diagnostics-content">
          <section v-if="build.linguistic_annotations" class="linguistic-provenance">
            <h4>{{ i18n.t("pdf_corpus.linguistic_analyzer_build") }}</h4>
            <dl>
              <div>
                <dt>{{ i18n.t("pdf_corpus.linguistic_analyzer_library") }}</dt>
                <dd>
                  {{
                    build.linguistic_annotations.engine === "spacy"
                      ? "spaCy"
                      : build.linguistic_annotations.engine || i18n.t("pdf_corpus.not_available")
                  }}
                  <template v-if="build.linguistic_annotations.engine_version">
                    · v{{ build.linguistic_annotations.engine_version }}
                  </template>
                </dd>
              </div>
              <div>
                <dt>{{ i18n.t("pdf_corpus.linguistic_analyzer_models") }}</dt>
                <dd>
                  {{
                    build.linguistic_annotations.models?.join(" · ") ||
                    i18n.t("pdf_corpus.not_available")
                  }}
                </dd>
              </div>
              <div>
                <dt>{{ i18n.t("pdf_corpus.linguistic_analyzer_languages") }}</dt>
                <dd>
                  {{
                    build.linguistic_annotations.languages?.join(" · ") ||
                    i18n.t("pdf_corpus.not_available")
                  }}
                </dd>
              </div>
              <div>
                <dt>{{ i18n.t("pdf_corpus.linguistic_analyzer_records") }}</dt>
                <dd>
                  {{
                    i18n.tf("pdf_corpus.linguistic_analyzer_records_value", {
                      done: build.linguistic_annotations.records_annotated || 0,
                      total: build.linguistic_annotations.records_total || 0,
                    })
                  }}
                </dd>
              </div>
            </dl>
            <p>{{ i18n.t("pdf_corpus.linguistic_analyzer_help") }}</p>
          </section>
          <CorpusDocumentIntelligenceStatus
            v-if="build.document_intelligence"
            :run="build.document_intelligence"
            :requested-provider="String(build.request?.document_nlp_provider || 'auto')"
          />
        </div>
      </details>

      <details class="diagnostics-section" @toggle="track('manifest', $event)">
        <summary>{{ i18n.t("pdf_corpus.diagnostics.manifest") }}</summary>
        <div v-if="opened.manifest" class="diagnostics-content">
          <div class="provenance-strip">
            <span
              >{{ i18n.t("pdf_corpus.build_id") }}: <code>{{ build.build_id }}</code></span
            >
            <span>SHA {{ build.source_sha256?.slice(0, 12) }}…</span>
            <span>{{ build.model || modelLabel || i18n.t("pdf_corpus.provider_default") }}</span>
            <span>{{ i18n.t("schemas.version") }} v{{ build.metadata_schema_version || "—" }}</span>
            <span>{{ build.segmentation_prompt_version }}</span>
          </div>
          <div v-if="runGuidance?.length" class="active-guidance-summary">
            <b>{{ i18n.t("pdf_corpus.run_guidance_title") }}</b>
            <ul>
              <li v-for="item in runGuidance" :key="item.field">
                <b>{{ item.label }}</b>
                <span v-if="item.instructions">{{ item.instructions }}</span>
                <small v-if="item.lookFor.length">{{ item.lookFor.join(" · ") }}</small>
              </li>
            </ul>
          </div>
          <slot name="manifest"></slot>
        </div>
      </details>

      <details class="diagnostics-section" @toggle="track('timeline', $event)">
        <summary>{{ i18n.t("pdf_corpus.diagnostics.timeline") }}</summary>
        <div v-if="opened.timeline" class="diagnostics-content">
          <CorpusBuildTimeline :build="build" />
        </div>
      </details>
    </div>
  </details>
</template>

<style scoped>
.corpus-build-diagnostics {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.corpus-build-diagnostics > summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: baseline;
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  font-weight: var(--fw-bold);
}
.corpus-build-diagnostics > summary small {
  color: var(--text-secondary);
  font-weight: normal;
}
.corpus-build-diagnostics summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -3px;
}
.diagnostics-body {
  display: grid;
  gap: var(--space-2);
  padding: 0 var(--space-4) var(--space-4);
}
.diagnostics-section {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.diagnostics-section > summary {
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.diagnostics-content {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
}
.linguistic-provenance {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.linguistic-provenance h4,
.linguistic-provenance p {
  margin: 0;
}
.linguistic-provenance h4 {
  font-size: var(--fs-sm);
}
.linguistic-provenance p {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  line-height: 1.5;
}
.linguistic-provenance dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2) var(--space-4);
  margin: 0;
}
.linguistic-provenance dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.linguistic-provenance dd {
  margin: 2px 0 0;
  overflow-wrap: anywhere;
  font-size: var(--fs-sm);
}
.provenance-strip {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.provenance-strip code {
  font-family: var(--font-mono, ui-monospace, monospace);
  overflow-wrap: anywhere;
}
.active-guidance-summary ul {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-1) 0 0;
  padding-inline-start: 1.2rem;
  font-size: var(--fs-sm);
}
.active-guidance-summary li {
  display: grid;
  gap: 2px;
}
.active-guidance-summary small {
  color: var(--text-secondary);
}
</style>

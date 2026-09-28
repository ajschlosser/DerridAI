<script setup lang="ts">
import { computed } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import CorpusSegmentationTelemetry from "./CorpusSegmentationTelemetry.vue";
import type { CorpusSegmentationTelemetry as CorpusSegmentationTelemetryData } from "../types/corpus";

const props = defineProps<{
  status: string;
  stage: string;
  progress: number;
  recordCount: number;
  reviewCount: number;
  acceptedCount: number;
  error?: string | null;
  warnings?: string[];
  /** Who acknowledged which warning, and when (keyed by warning ID). */
  warningAcknowledgements?: Record<
    string,
    { warning: string; acknowledged_by?: string; acknowledged_at?: string }
  >;
  validation?: CorpusBuild["validation"] | null;
  llmMetrics?: {
    calls?: number;
    manifest_calls?: number;
    segmentation_calls?: number;
    metadata_calls?: number;
    discourse_calls?: number;
    quotation_calls?: number;
    indexing_calls?: number;
    retries?: number;
    structured_output_failures?: number;
    escalations?: number;
  } | null;
  unresolvedCount?: number;
  metadataOperation?: CorpusBuild["metadata_operation"] | null;
  metadataActiveTasks?: Array<{ record_id?: string; task?: string; started_at?: string | null }>;
  metadataTasksTotal?: number;
  metadataTasksCompleted?: number;
  metadataTasksFailed?: number;
  metadataTasksSkipped?: number;
  metadataTasksRunning?: number;
  metadataTasksQueued?: number;
  boundaryCandidatesCompleted?: number;
  segmentationTelemetry?: CorpusSegmentationTelemetryData | null;
}>();
const i18n = useI18nStore();
function statusLabel() {
  return i18n.t(
    `pdf_corpus.status.${props.status}`,
    String(props.status || "unknown").replace(/_/g, " "),
  );
}
function stageLabel() {
  return i18n.t(
    `pdf_corpus.stage.${props.stage}`,
    String(props.stage || "unknown").replace(/_/g, " "),
  );
}
const validationReady = computed(() =>
  Boolean(
    props.validation &&
      typeof props.validation.valid === "boolean" &&
      ["review", "ready", "published"].includes(String(props.stage || "")),
  ),
);
const validationValid = computed(() => props.validation?.valid === true);
const validationCoverage = computed(() =>
  Math.round(Number(props.validation?.coverage || 0) * 100),
);
const validationEvidenceIssues = computed(() =>
  Number(props.validation?.metadata_evidence_errors?.length || 0),
);
const validationSchemaIssues = computed(() =>
  Number(props.validation?.metadata_schema_errors?.length || 0),
);
const validationPageLabelIssues = computed(() =>
  Number(props.validation?.printed_page_label_errors?.length || 0),
);
const validationTextFidelityIssues = computed(() =>
  Number(props.validation?.text_fidelity_errors?.length || 0),
);
const validationSourceOrderIssues = computed(() =>
  Number(props.validation?.source_order_errors?.length || 0),
);
const validationPageMappingIssues = computed(() =>
  Number(props.validation?.page_mapping_errors?.length || 0),
);
const validationCitationIssues = computed(() =>
  Number(props.validation?.citation_errors?.length || 0),
);
const stageExplanation = computed(() => {
  const stage = String(props.stage || "");
  const map: Record<string, string> = {
    preparing: "Preparing the durable build workspace and restoring any valid checkpoints.",
    resuming: "Restoring the last valid checkpoint before continuing the interrupted build.",
    structure: "Reading source structure and establishing document-level metadata.",
    document_review: "Finalizing document-level metadata before segmentation.",
    constructing_topology:
      "Preparing conserved SourceUnits and the semantic topology used to construct Records.",
    segmenting:
      "Generating boundary candidates deterministically and asking the LLM only bounded local split/keep questions where needed.",
    constructing_records:
      "Constructing reviewable Records from conserved SourceUnits, validating topology, indexing source units, and applying deterministic cleanup.",
    document_intelligence:
      "Analysing the complete reviewed document for derived entity, coreference, and quotation structure before record-level metadata enrichment.",
    reconciling: "Finalizing topology from an earlier compatible build checkpoint.",
    enriching:
      "Enriching each constructed Record with discourse, quotation, and indexing metadata. Source text and boundaries are already preserved.",
    finalizing_review:
      "Revalidating the completed build, updating review queues, and preparing the human-review workspace.",
    review: "Automated processing is complete. Review the proposed Records.",
    ready: "All quality gates have passed. The corpus is ready to publish.",
    published: "The reviewed corpus has been finalized as JSONL and is ready to download.",
  };
  return i18n.t(
    `pdf_corpus.stage_help.${stage}`,
    map[stage] || "Processing the current corpus-build stage.",
  );
});
const nextStage = computed(() => {
  const order = [
    "preparing",
    "structure",
    "document_review",
    "segmenting",
    "constructing_records",
    "document_intelligence",
    "enriching",
    "finalizing_review",
    "review",
    "ready",
    "published",
  ];
  const i = order.indexOf(String(props.stage || ""));
  return i >= 0 && i < order.length - 1
    ? i18n.t(`pdf_corpus.stage.${order[i + 1]}`, order[i + 1].replace(/_/g, " "))
    : "";
});
const currentOperation = computed(() => {
  const stage = String(props.stage || "");
  if (stage === "segmenting") {
    const total = Number(props.segmentationTelemetry?.candidateCount || 0);
    const completed = Number(props.boundaryCandidatesCompleted || 0);
    if (total > 0) {
      return i18n.tf("pdf_corpus.progress.boundary_candidates", {
        completed: Math.min(completed, total),
        total,
      });
    }
  }
  if (stage === "constructing_records") {
    return i18n.t("pdf_corpus.progress.constructing_detail");
  }
  if (stage === "document_intelligence") {
    return i18n.t("pdf_corpus.progress.document_intelligence_detail");
  }
  if (stage === "enriching") {
    const active = props.metadataActiveTasks || [];
    const total = Number(props.metadataTasksTotal || 0);
    const settled =
      Number(props.metadataTasksCompleted || 0) +
      Number(props.metadataTasksFailed || 0) +
      Number(props.metadataTasksSkipped || 0);
    if (active.length) {
      const first = active[0];
      return i18n.tf("pdf_corpus.progress.metadata_active", {
        record: first.record_id || "—",
        family: first.task || "metadata",
        active: Number(props.metadataTasksRunning || active.length),
        settled,
        total,
      });
    }
    if (total > 0) {
      return i18n.tf("pdf_corpus.progress.metadata_queue", {
        settled,
        total,
        running: Number(props.metadataTasksRunning || 0),
        queued: Number(props.metadataTasksQueued || 0),
      });
    }
  }
  if (stage === "finalizing_review") {
    return i18n.t("pdf_corpus.progress.finalizing_review_detail");
  }
  return "";
});

function acknowledgement(warning: string) {
  return Object.values(props.warningAcknowledgements || {}).find(
    (item) => item.warning === warning,
  );
}
function formatWhen(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(i18n.locale || undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}
</script>

<template>
  <section
    class="corpus-build-progress"
    :aria-label="i18n.t('pdf_corpus.build_progress')"
    aria-live="polite"
  >
    <div class="build-status-line">
      <span class="pill">{{ statusLabel() }}</span
      ><span>{{ i18n.t("pdf_corpus.stage") }}: {{ stageLabel() }}</span
      ><span>{{ props.recordCount }} {{ i18n.t("pdf_corpus.records") }}</span
      ><span>{{ props.reviewCount }} {{ i18n.t("pdf_corpus.need_review") }}</span
      ><span>{{ props.acceptedCount }} {{ i18n.t("pdf_corpus.accepted") }}</span>
    </div>
    <div v-if="Number(props.unresolvedCount || 0) > 0" class="unresolved-line" role="status">
      <b>{{ props.unresolvedCount }}</b>
      {{ i18n.t("pdf_corpus.unresolved_regions") }}
    </div>
    <div
      v-if="
        props.metadataOperation &&
        ['queued', 'running'].includes(String(props.metadataOperation.state || ''))
      "
      class="unresolved-line"
      role="status"
    >
      <b>{{ i18n.t("pdf_corpus.metadata_enrichment_in_progress") }}</b
      ><span
        >{{ props.metadataOperation.records_processed || 0 }} /
        {{ props.metadataOperation.records_total || 0 }}
        {{ i18n.t("pdf_corpus.records") }} · {{ props.metadataOperation.provider || "ollama" }} ·
        {{ props.metadataOperation.model || i18n.t("pdf_corpus.default_model") }}</span
      ><span v-if="props.metadataOperation.current_pass">{{
        i18n.tf("pdf_corpus.enrichment_pass_number", {
          pass: props.metadataOperation.current_pass,
        })
      }}</span
      ><span v-if="props.metadataOperation.records_reopened">{{
        i18n.tf("pdf_corpus.record_span_reopened_notice", {
          count: props.metadataOperation.records_reopened,
        })
      }}</span>
    </div>
    <div class="stage-explanation">
      <b>{{ stageLabel() }}</b
      ><span>{{ stageExplanation }}</span
      ><small v-if="nextStage">{{ i18n.t("pdf_corpus.next_stage") }}: {{ nextStage }}</small>
    </div>
    <div v-if="currentOperation" class="current-operation" role="status">
      <span>{{ i18n.t("pdf_corpus.progress.current_operation") }}</span>
      <b>{{ currentOperation }}</b>
    </div>
    <CorpusSegmentationTelemetry
      v-if="props.segmentationTelemetry"
      v-bind="props.segmentationTelemetry"
    />
    <div v-if="props.llmMetrics && Number(props.llmMetrics.calls || 0) > 0" class="llm-metrics">
      <span
        ><b>{{ props.llmMetrics.calls || 0 }}</b> {{ i18n.t("pdf_corpus.llm_calls") }}</span
      ><span v-if="props.llmMetrics.manifest_calls"
        >{{ props.llmMetrics.manifest_calls }} {{ i18n.t("pdf_corpus.manifest_calls") }}</span
      ><span v-if="props.llmMetrics.segmentation_calls"
        >{{ props.llmMetrics.segmentation_calls }}
        {{ i18n.t("pdf_corpus.segmentation_calls") }}</span
      ><span v-if="props.llmMetrics.metadata_calls"
        >{{ props.llmMetrics.metadata_calls }} {{ i18n.t("pdf_corpus.metadata_calls") }}</span
      ><span v-if="props.llmMetrics.retries"
        >{{ props.llmMetrics.retries }} {{ i18n.t("pdf_corpus.llm_retries") }}</span
      ><span v-if="props.llmMetrics.structured_output_failures"
        >{{ props.llmMetrics.structured_output_failures }}
        {{ i18n.t("pdf_corpus.structured_failures") }}</span
      ><span v-if="props.llmMetrics.escalations"
        >{{ props.llmMetrics.escalations }} {{ i18n.t("pdf_corpus.escalations") }}</span
      >
    </div>
    <div
      class="progress-track"
      role="progressbar"
      :aria-label="i18n.t('pdf_corpus.build_progress')"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="Math.round((props.progress || 0) * 100)"
      :aria-valuetext="
        i18n.tf('pdf_corpus.progress_percent', {
          percent: Math.round((props.progress || 0) * 100),
        })
      "
    >
      <span :style="{ width: `${Math.round((props.progress || 0) * 100)}%` }"></span>
    </div>
    <div v-if="props.error" class="build-warning" role="alert">
      <b>{{ i18n.t("pdf_corpus.build_error") }}</b
      ><span>{{ props.error }}</span>
    </div>
    <details v-if="props.warnings?.length" class="warnings">
      <summary>
        {{
          i18n.tf("pdf_corpus.warnings_count", {
            count: props.warnings.length,
          })
        }}
      </summary>
      <ul>
        <li v-for="warning in props.warnings" :key="warning">
          {{ warning
          }}<small v-if="acknowledgement(warning)" class="warning-acknowledged">{{
            i18n.tf("pdf_corpus.warning_acknowledged_by", {
              actor: acknowledgement(warning)?.acknowledged_by || "—",
              when: formatWhen(acknowledgement(warning)?.acknowledged_at),
            })
          }}</small>
        </li>
      </ul>
    </details>
    <div v-if="validationReady" class="validation-strip" :class="{ invalid: !validationValid }">
      <b>{{
        validationValid
          ? i18n.t("pdf_corpus.validation_passed")
          : i18n.t("pdf_corpus.validation_attention")
      }}</b
      ><span>{{ validationCoverage }}% {{ i18n.t("pdf_corpus.source_coverage") }}</span
      ><span v-if="validationEvidenceIssues"
        >{{ validationEvidenceIssues }} {{ i18n.t("pdf_corpus.evidence_issues") }}</span
      ><span v-if="validationSchemaIssues"
        >{{ validationSchemaIssues }} {{ i18n.t("pdf_corpus.schema_issues") }}</span
      ><span v-if="validationPageLabelIssues"
        >{{ validationPageLabelIssues }} {{ i18n.t("pdf_corpus.page_label_issues") }}</span
      >
    </div>
    <details v-if="validationReady && !validationValid" class="validation-details">
      <summary>{{ i18n.t("pdf_corpus.validation_details") }}</summary>
      <ul>
        <li v-if="validationTextFidelityIssues">
          {{ validationTextFidelityIssues }}
          {{ i18n.t("pdf_corpus.text_fidelity_issues") }}
        </li>
        <li v-if="validationSourceOrderIssues">
          {{ validationSourceOrderIssues }}
          {{ i18n.t("pdf_corpus.source_order_issues") }}
        </li>
        <li v-if="validationPageMappingIssues">
          {{ validationPageMappingIssues }}
          {{ i18n.t("pdf_corpus.page_mapping_issues") }}
        </li>
        <li v-if="validationSchemaIssues">
          {{ validationSchemaIssues }}
          {{ i18n.t("pdf_corpus.schema_issues") }}
        </li>
        <li v-if="validationCitationIssues">
          {{ validationCitationIssues }}
          {{ i18n.t("pdf_corpus.citation_issues") }}
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.corpus-build-progress {
  display: grid;
  gap: 9px;
}
.stage-explanation {
  display: grid;
  grid-template-columns: max-content 1fr max-content;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--soft);
  font-size: 0.8125rem;
}
.stage-explanation span {
  color: var(--muted);
  line-height: 1.4;
}
.stage-explanation small {
  color: var(--muted);
  white-space: nowrap;
}
.current-operation {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 8px 12px;
  align-items: baseline;
  padding: 9px 10px;
  border: 1px solid var(--tone-info-border);
  border-radius: 8px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: 0.8125rem;
}
.current-operation span {
  font-weight: 600;
}
.current-operation b {
  min-width: 0;
  overflow-wrap: anywhere;
}
.unresolved-line {
  padding: 7px 9px;
  border-radius: 8px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.build-status-line,
.validation-strip,
.llm-metrics {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  color: var(--muted);
}
.pill {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 7px;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.progress-track {
  height: 7px;
  border-radius: 999px;
  background: var(--soft);
  overflow: hidden;
}
.progress-track span {
  display: block;
  height: 100%;
  background: var(--accent);
  transition: width 0.25s;
}
.build-warning {
  display: grid;
  gap: 3px;
  padding: 9px;
  border: 1px solid var(--tone-danger-border);
  border-radius: 8px;
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.warning-acknowledged {
  display: block;
  color: var(--text-tertiary, var(--muted));
}
.warnings,
.validation-details {
  font-size: 0.8125rem;
}
.warnings summary,
.validation-details summary {
  cursor: pointer;
  font-weight: 700;
}
.validation-details ul {
  margin: 6px 0 0;
  padding-inline-start: 20px;
}
.validation-strip {
  padding: 7px 9px;
  border-radius: 8px;
  background: var(--tone-ok-bg);
}
.validation-strip.invalid {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
@media (max-width: 700px) {
  .stage-explanation,
  .current-operation {
    grid-template-columns: 1fr;
  }
  .stage-explanation small {
    white-space: normal;
  }
}
@media (prefers-reduced-motion: reduce) {
  .progress-track span {
    transition: none;
  }
}
</style>

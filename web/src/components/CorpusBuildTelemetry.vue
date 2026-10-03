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
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import CorpusSegmentationTelemetry from "./CorpusSegmentationTelemetry.vue";
import type { CorpusSegmentationTelemetry as CorpusSegmentationTelemetryData } from "../types/corpus";

const props = defineProps<{
  stage?: string;
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
  segmentationTelemetry?: CorpusSegmentationTelemetryData | null;
}>();
const i18n = useI18nStore();
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
</script>

<template>
  <section class="corpus-build-telemetry" :aria-label="i18n.t('pdf_corpus.build_telemetry')">
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
.corpus-build-telemetry {
  display: grid;
  gap: var(--space-2);
}
.unresolved-line {
  padding: var(--space-2);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
}
.validation-strip,
.llm-metrics {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  flex-wrap: wrap;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}
.validation-details {
  font-size: var(--fs-sm);
}
.validation-details summary {
  cursor: pointer;
  font-weight: var(--fw-bold);
}
.validation-details ul {
  margin: var(--space-2) 0 0;
  padding-inline-start: 20px;
}
.validation-strip {
  padding: var(--space-2);
  border-radius: var(--radius-control);
  background: var(--tone-ok-bg);
}
.validation-strip.invalid {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
</style>

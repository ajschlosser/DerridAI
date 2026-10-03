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
import { computed } from "vue";
import UiButton from "../ui/UiButton.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { pipelineComparisonRows } from "../../domain/pipelineStudioPresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  ResearchPipelineComparisonResult,
  ResearchPipelineComparisonSide,
} from "../../types/pipelines";

// The one A/B result view, shared by the ad-hoc comparison and the fixed benchmark. It describes
// differences only; it never names a better pipeline.
const props = defineProps<{
  result: ResearchPipelineComparisonResult;
  /** Present when the result belongs to a saved benchmark run. */
  benchmarkMeta?: {
    benchmarkRunId: string;
    caseId: string;
    caseVersion: number;
    corpusFingerprint: string;
    warnings?: string[];
  } | null;
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const rows = computed(() => pipelineComparisonRows(props.result));

function percent(value: number) {
  return new Intl.NumberFormat(i18n.locale, { style: "percent", maximumFractionDigits: 0 }).format(
    value,
  );
}
function seconds(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value.toFixed(value < 10 ? 2 : 1)} s`;
}
function sideTitle(side: ResearchPipelineComparisonSide) {
  return `${side.pipeline.name || side.pipeline.pipeline_id || "—"} · v${side.pipeline.pipeline_version ?? "—"}`;
}
function sidePipelineKey(side: ResearchPipelineComparisonSide) {
  const id = side.pipeline.pipeline_id;
  const version = side.pipeline.pipeline_version;
  return id && version != null ? `${id}@${version}` : "";
}
function sideFlow(side: ResearchPipelineComparisonSide) {
  return `${side.candidates.pre_rerank.count} → ${side.candidates.post_rerank.count} → ${side.evidence.length}`;
}
function resources(side: ResearchPipelineComparisonSide) {
  return t(
    "pipelines.compare_resources",
    "Context: {context} characters · Cross-encoder calls: {calls}",
  )
    .replace("{context}", String(side.context_characters ?? "—"))
    .replace("{calls}", String(side.resource_use.cross_encoder_calls));
}
</script>

<template>
  <section class="comparison-result" aria-labelledby="pipeline-comparison-result-title">
    <dl class="comparison-overview">
      <div>
        <dt class="metric-label">
          {{ t("pipelines.compare_candidate_overlap", "Candidate-pool overlap") }}
          <UiTooltip
            :text="
              t(
                'pipelines.compare_candidate_overlap_help',
                'This compares the unique candidate Record IDs presented to reranking on both sides. It shows whether the retrieval stages found the same material before later ranking and provenance checks.',
              )
            "
          />
        </dt>
        <dd id="pipeline-comparison-result-title">
          <strong>{{ percent(result.comparison.candidate_overlap.jaccard_overlap) }}</strong>
          <small>
            {{ result.comparison.candidate_overlap.shared_count }} /
            {{ result.comparison.candidate_overlap.union_count }}
            {{ t("pipelines.compare_shared_union", "shared / distinct records") }}
          </small>
        </dd>
      </div>
      <div>
        <dt class="metric-label">
          {{ t("pipelines.compare_overlap", "Final evidence overlap") }}
          <UiTooltip
            :text="
              t(
                'pipelines.compare_overlap_help',
                'Jaccard overlap compares the final evidence record IDs selected by both pipelines: shared records divided by all distinct records. It measures similarity between outputs, not scholarly quality.',
              )
            "
          />
        </dt>
        <dd>
          <strong>{{ percent(result.comparison.jaccard_overlap) }}</strong>
          <small>
            {{ result.comparison.shared_count }} / {{ result.comparison.union_count }}
            {{ t("pipelines.compare_shared_union", "shared / distinct records") }}
          </small>
        </dd>
      </div>
      <div>
        <dt class="metric-label">{{ t("pipelines.compare_left_time", "Pipeline A time") }}</dt>
        <dd>
          <strong>{{ seconds(result.left.elapsed_seconds) }}</strong>
        </dd>
      </div>
      <div>
        <dt class="metric-label">{{ t("pipelines.compare_right_time", "Pipeline B time") }}</dt>
        <dd>
          <strong>{{ seconds(result.right.elapsed_seconds) }}</strong>
        </dd>
      </div>
    </dl>
    <p class="interpretation">
      {{
        t(
          "pipelines.compare_overlap_interpretation",
          "Overlap describes how similar the selected evidence sets are; it does not measure scholarly quality.",
        )
      }}
    </p>

    <div class="side-grid">
      <section v-for="(side, key) in { A: result.left, B: result.right }" :key="key" class="side">
        <div class="side-heading">
          <div>
            <p class="side-kicker">
              {{
                key === "A"
                  ? t("pipelines.compare_left", "Pipeline A")
                  : t("pipelines.compare_right", "Pipeline B")
              }}
            </p>
            <h4>{{ sideTitle(side) }}</h4>
          </div>
          <UiButton
            v-if="sidePipelineKey(side)"
            variant="ghost"
            size="small"
            :label="t('pipelines.open_configuration', 'Open configuration')"
            @click="emit('openPipeline', sidePipelineKey(side))"
          />
        </div>
        <p>
          {{ t("pipelines.compare_flow", "Candidates: pre-rerank → reranked → final evidence") }}
          <strong>{{ sideFlow(side) }}</strong>
        </p>
        <p>{{ resources(side) }}</p>
        <ul v-if="side.warnings.length" class="side-warnings">
          <li v-for="warning in side.warnings" :key="warning">{{ warning }}</li>
        </ul>
      </section>
    </div>

    <section class="aligned" aria-labelledby="pipeline-comparison-records-title">
      <h4 id="pipeline-comparison-records-title">
        {{ t("pipelines.compare_aligned_records", "Final evidence, aligned by record") }}
      </h4>
      <p v-if="!rows.length" class="empty">
        {{ t("pipelines.compare_no_evidence", "Neither pipeline selected final evidence.") }}
      </p>
      <div v-else class="table-shell">
        <table>
          <thead>
            <tr>
              <th scope="col">{{ t("pipelines.compare_record", "Record") }}</th>
              <th scope="col">{{ t("pipelines.compare_left", "Pipeline A") }}</th>
              <th scope="col">{{ t("pipelines.compare_right", "Pipeline B") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.recordId" :data-presence="row.presence">
              <th scope="row">
                <code>{{ row.recordId }}</code>
                <small>{{
                  (row.left || row.right)?.work || (row.left || row.right)?.citation || "—"
                }}</small>
                <small v-if="row.presence === 'left'" class="presence">
                  {{ t("pipelines.compare_only_left", "Only in Pipeline A") }}
                </small>
                <small v-else-if="row.presence === 'right'" class="presence">
                  {{ t("pipelines.compare_only_right", "Only in Pipeline B") }}
                </small>
              </th>
              <td>{{ row.left ? `#${row.left.rank}` : "—" }}</td>
              <td>{{ row.right ? `#${row.right.rank}` : "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <details class="provenance" :open="Boolean(benchmarkMeta?.warnings?.length)">
      <summary>{{ t("pipelines.compare_provenance", "Provenance") }}</summary>
      <dl>
        <template v-if="benchmarkMeta">
          <div>
            <dt>{{ t("pipelines.benchmark_saved", "Saved benchmark") }}</dt>
            <dd>{{ benchmarkMeta.caseId }} · v{{ benchmarkMeta.caseVersion }}</dd>
          </div>
          <div>
            <dt>{{ t("pipelines.benchmark_run_id", "Benchmark run ID") }}</dt>
            <dd>
              <code>{{ benchmarkMeta.benchmarkRunId }}</code>
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.benchmark_corpus_fingerprint", "Corpus/index fingerprint") }}</dt>
            <dd>
              <code>{{ benchmarkMeta.corpusFingerprint }}</code>
            </dd>
          </div>
        </template>
        <div>
          <dt>{{ t("pipelines.compare_left", "Pipeline A") }}</dt>
          <dd>
            <code>{{ result.left.pipeline.pipeline_hash || "—" }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.compare_right", "Pipeline B") }}</dt>
          <dd>
            <code>{{ result.right.pipeline.pipeline_hash || "—" }}</code>
          </dd>
        </div>
      </dl>
      <div v-if="benchmarkMeta?.warnings?.length" class="warnings">
        <strong>{{
          t("pipelines.benchmark_reproducibility_limits", "Reproducibility limits")
        }}</strong>
        <ul>
          <li v-for="warning in benchmarkMeta.warnings" :key="warning">{{ warning }}</li>
        </ul>
      </div>
    </details>
  </section>
</template>

<style scoped>
.comparison-result {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
.comparison-overview {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-6, 28px);
  margin: 0;
  padding: var(--space-3) 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.comparison-overview > div {
  display: grid;
  gap: 2px;
}
.comparison-overview dd {
  display: grid;
  margin: 0;
}
.comparison-overview strong {
  color: var(--text-primary);
  font-size: 1.375rem;
  font-variant-numeric: tabular-nums;
}
.comparison-overview small,
.metric-label,
.side-kicker,
.interpretation,
.empty {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.metric-label {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-weight: var(--fw-bold);
}
.interpretation {
  margin: calc(var(--space-2) * -1) 0 0;
}
.side-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}
.side-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}
.side-heading > div {
  min-width: 0;
}
.side p {
  margin: 0 0 var(--space-1);
  color: var(--text-secondary);
  font-size: 0.875rem;
}
.side-kicker {
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.side h4,
.aligned h4 {
  margin: 0 0 var(--space-1);
  color: var(--text-primary);
  font-size: 1rem;
}
.side-warnings,
.warnings ul {
  margin: var(--space-1) 0 0;
  padding-left: var(--space-4);
  color: var(--tone-warn-fg);
  font-size: 0.875rem;
}
.table-shell {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
th,
td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  text-align: left;
  vertical-align: top;
}
thead th {
  background: var(--surface-inset);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
tbody tr:last-child > * {
  border-bottom: 0;
}
tbody th {
  display: grid;
  gap: 2px;
  font-weight: var(--fw-regular);
}
tbody th small {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
tbody td {
  font-variant-numeric: tabular-nums;
}
.presence {
  font-weight: var(--fw-bold);
}
.provenance summary {
  width: fit-content;
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: var(--fw-bold);
  cursor: pointer;
}
.provenance summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.provenance dl {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-2) 0 0;
}
.provenance dl > div {
  display: grid;
  gap: 2px;
}
.provenance dt {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.provenance dd {
  margin: 0;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.provenance code {
  font-size: 0.75rem;
}
.warnings {
  margin-top: var(--space-2);
  color: var(--tone-warn-fg);
  font-size: 0.875rem;
}
@media (max-width: 680px) {
  .side-grid {
    grid-template-columns: 1fr;
  }
}
</style>

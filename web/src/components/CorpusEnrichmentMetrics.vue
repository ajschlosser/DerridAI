<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import { pdfCorpusApi, type EnrichmentMetrics, type EnrichmentModelMetrics } from "../api/pdfCorpus";
import UiButton from "./ui/UiButton.vue";

// Measurements of enrichment for one build, loaded on request: this is analysis, not part of the
// review flow, so it should not cost a request every time the workspace opens.
const props = defineProps<{ buildId: string }>();
const i18n = useI18nStore();
const metrics = ref<EnrichmentMetrics | null>(null);
const loading = ref(false);
const failed = ref("");

const rows = computed(() => Object.entries(metrics.value?.models ?? {}));
const na = computed(() => i18n.t("pdf_corpus.enrich_metrics.na", "not enough data"));
const pct = (value: number | null | undefined) => (value == null ? na.value : `${Math.round(value * 100)}%`);
const seconds = (value: number | null | undefined) => (value == null ? na.value : `${(value / 1000).toFixed(1)} s`);
const brier = (value: number | null | undefined) => (value == null ? na.value : value.toFixed(3));
const at90 = (m: EnrichmentModelMetrics) => m.precision_at_threshold.find((t) => t.threshold === 0.9);
const t = (key: string, fallback: string) => i18n.t(`pdf_corpus.enrich_metrics.${key}`, fallback);

async function load() {
  loading.value = true;
  failed.value = "";
  try {
    metrics.value = await pdfCorpusApi.enrichmentMetrics(props.buildId);
  } catch (error) {
    failed.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <details class="enrich-metrics" @toggle="(e) => (e.target as HTMLDetailsElement).open && !metrics && load()">
    <summary>{{ t("title", "How well is enrichment working?") }}</summary>
    <p v-if="loading" role="status">{{ t("loading", "Measuring…") }}</p>
    <p v-else-if="failed" role="alert">{{ failed }} <UiButton :label="t('load', 'Load measurements')" @click="load" /></p>
    <p v-else-if="metrics && !rows.length">{{ t("none", "Nothing has been measured yet. Run a pass and review some values first.") }}</p>
    <template v-else-if="metrics">
      <div class="enrich-scroll" tabindex="0" role="region" :aria-label="t('title', 'How well is enrichment working?')">
        <table>
          <thead>
            <tr>
              <th scope="col">{{ t("model", "Model") }}</th>
              <th scope="col">{{ t("proposals", "Proposed") }}</th>
              <th scope="col">{{ t("reviews", "Reviewed") }}</th>
              <th scope="col">{{ t("acceptance", "Kept as proposed") }}</th>
              <th scope="col">{{ t("corrections", "Corrected") }}</th>
              <th scope="col">{{ t("cleared", "Cleared") }}</th>
              <th scope="col" :title="t('help_brier', '0 is perfect and 0.25 is a coin toss. Lower means its confidence can be trusted.')">{{ t("brier", "Calibration error (Brier)") }}</th>
              <th scope="col">{{ t("precision90", "Right when 90%+ sure") }}</th>
              <th scope="col">{{ t("coverage90", "Values 90%+ sure") }}</th>
              <th scope="col">{{ t("grounded", "Cited a real source") }}</th>
              <th scope="col">{{ t("touched", "Still needed a person") }}</th>
              <th scope="col">{{ t("stability", "Same answer across runs") }}</th>
              <th scope="col">{{ t("ms_accepted", "Time per kept value") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="[model, m] in rows" :key="model">
              <th scope="row">{{ model || "—" }}</th>
              <td>{{ m.proposals }}</td>
              <td>{{ m.reviews }}</td>
              <td>{{ pct(m.acceptance_rate) }}</td>
              <td>{{ pct(m.correction_rate) }}</td>
              <td>{{ pct(m.rejection_rate) }}</td>
              <td>{{ brier(m.brier_score) }}</td>
              <td>{{ pct(at90(m)?.precision) }}</td>
              <td>{{ pct(at90(m)?.coverage) }}</td>
              <td>{{ pct(m.grounded_rate) }}</td>
              <td>{{ pct(m.touched_share) }}</td>
              <td>{{ pct(m.stability) }}</td>
              <td>{{ seconds(m.ms_per_accepted_field) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <dl class="enrich-facts">
        <div><dt>{{ t("agreement", "Models agreeing on the same field") }}</dt><dd>{{ pct(metrics.inter_model_agreement.agreement) }} ({{ metrics.inter_model_agreement.compared }})</dd></div>
        <div><dt>{{ t("unresolved", "Fields still waiting for a person") }}</dt><dd>{{ metrics.unresolved_remaining ?? na }}</dd></div>
        <div><dt>{{ t("concurrency", "Runs working now / limit") }}</dt><dd>{{ metrics.concurrency.working }} / {{ metrics.concurrency.limit }}</dd></div>
      </dl>
    </template>
  </details>
</template>

<style scoped>
.enrich-metrics { border: 1px solid var(--line); border-radius: 12px; background: var(--card); padding: 0.5rem 0.875rem; }
.enrich-metrics summary { cursor: pointer; font-weight: 700; padding: 0.375rem 0; }
.enrich-metrics summary:focus-visible, .enrich-scroll:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; }
.enrich-scroll { overflow-x: auto; margin-block: 0.5rem; }
table { border-collapse: collapse; inline-size: 100%; font-size: 0.8125rem; }
th, td { padding: 0.375rem 0.625rem; border-block-end: 1px solid var(--line); text-align: start; white-space: nowrap; }
thead th { color: var(--text-2); font-weight: 650; white-space: normal; min-inline-size: 6rem; vertical-align: bottom; }
.enrich-facts { display: grid; gap: 0.25rem; margin: 0.5rem 0 0.25rem; font-size: 0.8125rem; }
.enrich-facts div { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.enrich-facts dt { color: var(--text-2); }
.enrich-facts dd { margin: 0; font-weight: 700; }
</style>

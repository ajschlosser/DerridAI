<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import { pdfCorpusApi, type EnrichmentMetrics, type EnrichmentModelMetrics, type Interval } from "../api/pdfCorpus";
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
const span = (value: Interval | undefined) =>
  !value || value.rate == null ? na.value : `${Math.round(value.rate * 100)}% (${Math.round((value.low ?? 0) * 100)}–${Math.round((value.high ?? 0) * 100)}%, n=${value.n})`;
const minutes = (value: number | null | undefined) => (value == null ? na.value : `${Math.round(value)} s`);
const at90 = (m: EnrichmentModelMetrics) => m.precision_at_threshold.find((t) => t.threshold === 0.9);
const t = (key: string, fallback: string) => i18n.t(`pdf_corpus.enrich_metrics.${key}`, fallback);
const empty = (value: string) => value === na.value;
const rateTone = (value: number | null | undefined, invert = false) => {
  if (value == null) return "empty";
  const score = invert ? 1 - value : value;
  if (score >= 0.8) return "ok";
  if (score >= 0.5) return "warn";
  return "danger";
};
const brierTone = (value: number | null | undefined) => {
  if (value == null) return "empty";
  if (value <= 0.1) return "ok";
  if (value <= 0.2) return "warn";
  return "danger";
};
const spotChecks = computed(() =>
  rows.value.reduce((sum, [, m]) => sum + Number(m.spot_checks_still_needed || 0), 0),
);
const unresolved = computed(() => metrics.value?.unresolved_remaining ?? null);

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
      <div class="next-work" role="group" :aria-label="t('next_work', 'What still needs a person')">
        <article :data-tone="Number(unresolved) > 0 ? 'warn' : 'ok'">
          <strong>{{ unresolved ?? na }}</strong>
          <span>{{ t("unresolved", "Fields still waiting for a person") }}</span>
        </article>
        <article :data-tone="spotChecks > 0 ? 'warn' : 'ok'">
          <strong>{{ spotChecks }}</strong>
          <span>{{ t("spot_checks", "Spot checks still to do") }}</span>
        </article>
        <article data-tone="neutral">
          <strong>{{ metrics.concurrency.working }} / {{ metrics.concurrency.limit }}</strong>
          <span>{{ t("concurrency", "Runs working now / limit") }}</span>
        </article>
      </div>
      <div class="verdicts">
        <section v-for="[model, m] in rows" :key="`verdict-${model}`" class="verdict-model">
          <p class="verdict-model-name">{{ model || "—" }}</p>
          <p>{{ i18n.tf("pdf_corpus.enrich_metrics.verdict_sample", "{reviews} reviewed of {proposed} proposed", { reviews: m.reviews, proposed: m.proposals }) }}</p>
          <div class="verdict-grid">
            <article :data-tone="rateTone(m.acceptance_rate)">
              <span>{{ t("verdict_trust", "Trust") }}</span>
              <b>{{ pct(m.acceptance_rate) }}</b>
              <small>{{ t("acceptance", "Kept as proposed") }} · {{ t("substantive", "Substantively wrong (95% range)") }} {{ span(m.substantive_error_rate) }}</small>
              <small>{{ t("brier", "Calibration error (Brier)") }} {{ brier(m.brier_score) }} · {{ t("precision90", "Right when 90%+ sure") }} {{ pct(at90(m)?.precision) }}</small>
            </article>
            <article :data-tone="rateTone(m.grounded_rate)">
              <span>{{ t("verdict_grounding", "Grounding") }}</span>
              <b>{{ pct(m.grounded_rate) }}</b>
              <small>{{ t("grounded", "Cited a real source") }} · {{ t("supported", "Names found in the text") }} {{ pct(m.supported_rate) }} ({{ m.supported_checked }})</small>
              <small>{{ t("coverage90", "Values 90%+ sure") }} {{ pct(at90(m)?.coverage) }} · {{ t("touched", "Still needed a person") }} {{ pct(m.touched_share) }}</small>
            </article>
            <article data-tone="neutral">
              <span>{{ t("verdict_effort", "Effort") }}</span>
              <b>{{ seconds(m.ms_per_accepted_field) }}</b>
              <small>{{ t("ms_accepted", "Time per kept value") }} · {{ t("review_time", "Review time per decision") }} {{ minutes(m.review_seconds_per_decision) }}</small>
              <small>{{ t("first_value", "Time to first useful value") }} {{ minutes(m.seconds_to_first_useful_value) }}</small>
            </article>
          </div>
        </section>
      </div>
      <p class="sparse-note">{{ t("sparse_note", "Every measurement stays in the tables below, including cells that still say there is not enough data.") }}</p>
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
              <td class="num">{{ m.proposals }}</td>
              <td class="num">{{ m.reviews }}</td>
              <td class="num" :data-tone="rateTone(m.acceptance_rate)">{{ pct(m.acceptance_rate) }}</td>
              <td class="num">{{ pct(m.correction_rate) }}</td>
              <td class="num">{{ pct(m.rejection_rate) }}</td>
              <td class="num" :data-tone="brierTone(m.brier_score)">{{ brier(m.brier_score) }}</td>
              <td class="num" :data-tone="rateTone(at90(m)?.precision)">{{ pct(at90(m)?.precision) }}</td>
              <td class="num" :class="{ empty: empty(pct(at90(m)?.coverage)) }">{{ pct(at90(m)?.coverage) }}</td>
              <td class="num" :data-tone="rateTone(m.grounded_rate)">{{ pct(m.grounded_rate) }}</td>
              <td class="num">{{ pct(m.touched_share) }}</td>
              <td class="num" :class="{ empty: empty(pct(m.stability)) }">{{ pct(m.stability) }}</td>
              <td class="num">{{ seconds(m.ms_per_accepted_field) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="enrich-scroll" tabindex="0" role="region" :aria-label="t('trust_title', 'Trust, effort and cost')">
        <table>
          <caption>{{ t("trust_title", "Trust, effort and cost") }}</caption>
          <thead>
            <tr>
              <th scope="col">{{ t("model", "Model") }}</th>
              <th scope="col">{{ t("acceptance_ci", "Kept as proposed (95% range)") }}</th>
              <th scope="col">{{ t("substantive", "Substantively wrong (95% range)") }}</th>
              <th scope="col">{{ t("autofill_precision", "Autofilled values that held up") }}</th>
              <th scope="col">{{ t("spot_checks", "Spot checks still to do") }}</th>
              <th scope="col">{{ t("repeats", "Repeated a rejected value") }}</th>
              <th scope="col">{{ t("supported", "Names found in the text") }}</th>
              <th scope="col">{{ t("review_time", "Review time per decision") }}</th>
              <th scope="col">{{ t("first_value", "Time to first useful value") }}</th>
              <th scope="col">{{ t("suspensions", "Autofill switched off / on") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="[model, m] in rows" :key="model">
              <th scope="row">{{ model || "—" }}</th>
              <td :class="{ empty: empty(span(m.acceptance_ci)) }">{{ span(m.acceptance_ci) }}</td>
              <td :class="{ empty: empty(span(m.substantive_error_rate)) }">{{ span(m.substantive_error_rate) }}</td>
              <td :class="{ empty: empty(span(m.autofill_precision_ci)) }">{{ span(m.autofill_precision_ci) }}</td>
              <td class="num">{{ m.spot_checks_still_needed }}</td>
              <td :class="{ empty: empty(pct(m.repeat_rate)) }">{{ pct(m.repeat_rate) }} ({{ m.proposals_after_a_rejection }})</td>
              <td>{{ pct(m.supported_rate) }} ({{ m.supported_checked }})</td>
              <td class="num">{{ minutes(m.review_seconds_per_decision) }}</td>
              <td class="num">{{ minutes(m.seconds_to_first_useful_value) }}</td>
              <td class="num">{{ m.autofill_suspensions }} / {{ m.autofill_resumptions }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="enrich-export"><a href="/api/pdf/corpus-enrichment-ledger.csv" download>{{ t("export", "Download every event as CSV") }}</a></p>
      <dl class="enrich-facts">
        <div><dt>{{ t("agreement", "Models agreeing on the same field") }}</dt><dd :class="{ empty: empty(pct(metrics.inter_model_agreement.agreement)) }">{{ pct(metrics.inter_model_agreement.agreement) }} ({{ metrics.inter_model_agreement.compared }})</dd></div>
        <div><dt>{{ t("self_consistency", "Reviewer gave the same answer when asked again") }}</dt><dd :class="{ empty: empty(span(metrics.self_consistency)) }">{{ span(metrics.self_consistency) }}</dd></div>
        <div><dt>{{ t("inter_annotator", "Two reviewers agreed (second one blind)") }}</dt><dd :class="{ empty: empty(span(metrics.inter_annotator)) }">{{ span(metrics.inter_annotator) }}<template v-if="metrics.inter_annotator?.kappa != null"> · κ {{ metrics.inter_annotator.kappa.toFixed(2) }}</template></dd></div>
        <div><dt>{{ t("unresolved", "Fields still waiting for a person") }}</dt><dd>{{ metrics.unresolved_remaining ?? na }}</dd></div>
        <div><dt>{{ t("concurrency", "Runs working now / limit") }}</dt><dd>{{ metrics.concurrency.working }} / {{ metrics.concurrency.limit }}</dd></div>
      </dl>
    </template>
  </details>
</template>

<style scoped>
.enrich-metrics { border: 1px solid var(--line); border-radius: 12px; background: var(--card); padding: 0.5rem 0.875rem 0.75rem; }
.enrich-metrics summary { cursor: pointer; font-weight: 700; padding: 0.375rem 0; }
.enrich-metrics summary:focus-visible, .enrich-scroll:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; }
.next-work { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0.5rem 0 0.75rem; }
.next-work article, .verdict-grid article { display: grid; gap: 2px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--soft); }
.next-work strong, .verdict-grid b { font-size: 1.25rem; line-height: 1.15; font-variant-numeric: tabular-nums; }
.next-work span, .verdict-grid span, .verdict-grid small { font-size: 0.8125rem; color: var(--muted); line-height: 1.4; }
.next-work article[data-tone="warn"], .verdict-grid article[data-tone="warn"], td[data-tone="warn"] { border-color: var(--tone-warn-edge); background: var(--tone-warn-bg); color: var(--tone-warn-fg); }
.next-work article[data-tone="ok"], .verdict-grid article[data-tone="ok"], td[data-tone="ok"] { border-color: var(--tone-ok-edge); background: var(--tone-ok-bg); color: var(--tone-ok-fg); }
.verdict-grid article[data-tone="danger"], td[data-tone="danger"] { border-color: var(--tone-danger-edge); background: var(--tone-danger-bg); color: var(--tone-danger-fg); }
.next-work article[data-tone="warn"] span, .verdict-grid article[data-tone="warn"] small, .verdict-grid article[data-tone="ok"] small { color: inherit; }
.verdict-model { display: grid; gap: 6px; margin-bottom: 0.75rem; }
.verdict-model-name { margin: 0; font-size: 0.875rem; font-weight: 700; overflow-wrap: anywhere; }
.verdict-model > p { margin: 0; font-size: 0.8125rem; color: var(--muted); }
.verdict-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.verdict-grid span { font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; }
.sparse-note { margin: 0 0 0.5rem; font-size: 0.8125rem; color: var(--muted); }
.enrich-scroll { overflow-x: auto; margin-block: 0.5rem; }
table { border-collapse: collapse; inline-size: 100%; font-size: 0.8125rem; }
th, td { padding: 0.375rem 0.625rem; border-block-end: 1px solid var(--line); text-align: start; }
thead th { color: var(--text-2); font-weight: 650; white-space: normal; min-inline-size: 5.5rem; vertical-align: bottom; }
th[scope="row"] { position: sticky; inset-inline-start: 0; background: var(--card); z-index: 1; min-inline-size: 10rem; max-inline-size: 16rem; white-space: normal; overflow-wrap: anywhere; }
.num { text-align: end; font-variant-numeric: tabular-nums; white-space: nowrap; }
.empty, dd.empty { color: var(--muted); font-weight: 500; }
.enrich-facts { display: grid; gap: 0.35rem; margin: 0.5rem 0 0.25rem; font-size: 0.8125rem; }
.enrich-facts div { display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 6px 8px; border-radius: 8px; background: var(--soft); }
.enrich-export { margin: 0.5rem 0 0; font-size: 0.8125rem; }
.enrich-export a { color: var(--accent-fg); font-weight: 700; }
caption { text-align: start; font-weight: 700; padding-block: 0.375rem; }
.enrich-facts dt { color: var(--text-2); }
.enrich-facts dd { margin: 0; font-weight: 700; }
@media (max-width: 900px) {
  .next-work, .verdict-grid { grid-template-columns: 1fr; }
}
</style>

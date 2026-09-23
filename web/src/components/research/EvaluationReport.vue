<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{ report: unknown }>();
const i18n = useI18nStore();
const CATEGORY_KEYS = [
  "query_relevance",
  "source_binding",
  "claim_traceability",
  "attribution_source_discrimination",
  "claim_evidence_fidelity",
  "conceptual_precision",
  "coverage",
  "interpretive_usefulness",
] as const;

type AnyRecord = Record<string, unknown>;
function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as AnyRecord) : {};
}
function unwrap(value: unknown): AnyRecord {
  let current = asRecord(value);
  for (let i = 0; i < 4; i++) {
    if (current.grade && typeof current.grade === "object") {
      current = asRecord(current.grade);
      continue;
    }
    if (
      current.result &&
      typeof current.result === "object" &&
      !("overall" in current || "categories" in current || "summary" in current)
    ) {
      current = asRecord(current.result);
      continue;
    }
    break;
  }
  return current;
}
const grade = computed(() => unwrap(props.report));
const categories = computed(() => asRecord(grade.value.categories));
function scoreFor(key: string): number | null {
  const direct = grade.value[key];
  const category = asRecord(categories.value[key]);
  const raw = category.score ?? direct;
  const numeric = Number(raw);
  return Number.isFinite(numeric) ? Math.max(0, Math.min(10, numeric)) : null;
}
const overall = computed(() => scoreFor("overall"));
function categoryAnalysis(key: string) {
  const value = asRecord(categories.value[key]).analysis;
  return typeof value === "string" ? value.trim() : "";
}
function listValue(key: string): string[] {
  const value = grade.value[key];
  if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean);
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}
const strengths = computed(() => listValue("strengths"));
const weaknesses = computed(() => listValue("weaknesses"));
const risky = computed(() => listValue("unsupported_or_risky_claims"));
const summary = computed(() => String(grade.value.summary || "").trim());
const analysis = computed(() => String(grade.value.analysis || "").trim());
const rawOutput = computed(() => grade.value.raw_output ?? props.report);
function formatJson(value: unknown) {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return String(value ?? "");
  }
}
function categoryLabel(key: string) {
  return i18n.t(
    `faq.grade_${key}`,
    key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase()),
  );
}
function scoreText(score: number | null) {
  return score == null ? "—" : Number.isInteger(score) ? String(score) : score.toFixed(1);
}
</script>

<template>
  <section
    class="evaluation-report"
    :aria-label="i18n.t('faq.evaluation_report', 'Evaluation report')"
  >
    <header class="evaluation-report-hero">
      <div
        class="evaluation-score"
        :aria-label="
          i18n.tf('faq.overall_score', 'Overall score: {score} out of 10', {
            score: scoreText(overall),
          })
        "
      >
        <strong>{{ scoreText(overall) }}</strong
        ><span>/10</span>
      </div>
      <div>
        <span class="evaluation-kicker">{{
          i18n.t("faq.evaluation_report", "Evaluation report")
        }}</span>
        <h3>
          {{
            summary ||
            i18n.t("faq.grade_summary_fallback", "Structured evidence-grounding assessment")
          }}
        </h3>
        <p v-if="analysis">{{ analysis }}</p>
      </div>
    </header>

    <section
      class="evaluation-categories"
      :aria-label="i18n.t('faq.grade_categories', 'Scoring categories')"
    >
      <article v-for="key in CATEGORY_KEYS" :key="key" class="evaluation-category">
        <div class="evaluation-category-head">
          <strong>{{ categoryLabel(key) }}</strong
          ><span>{{ scoreText(scoreFor(key)) }}<small>/10</small></span>
        </div>
        <div
          class="evaluation-meter"
          role="meter"
          :aria-label="categoryLabel(key)"
          aria-valuemin="0"
          aria-valuemax="10"
          :aria-valuenow="scoreFor(key) ?? undefined"
        >
          <i :style="{ width: `${(scoreFor(key) ?? 0) * 10}%` }"></i>
        </div>
        <p v-if="categoryAnalysis(key)">{{ categoryAnalysis(key) }}</p>
      </article>
    </section>

    <div v-if="strengths.length || weaknesses.length || risky.length" class="evaluation-findings">
      <section v-if="strengths.length" class="evaluation-finding positive">
        <header>
          <AppIcon name="check" />
          <h4>{{ i18n.t("faq.grade_strengths", "Strengths") }}</h4>
        </header>
        <ul>
          <li v-for="item in strengths" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section v-if="weaknesses.length" class="evaluation-finding">
        <header>
          <AppIcon name="warning" />
          <h4>{{ i18n.t("faq.grade_weaknesses", "Weaknesses") }}</h4>
        </header>
        <ul>
          <li v-for="item in weaknesses" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section v-if="risky.length" class="evaluation-finding risk">
        <header>
          <AppIcon name="warning" />
          <h4>{{ i18n.t("faq.grade_risky_claims", "Unsupported or risky claims") }}</h4>
        </header>
        <ul>
          <li v-for="item in risky" :key="item">{{ item }}</li>
        </ul>
      </section>
    </div>

    <details class="evaluation-raw">
      <summary>{{ i18n.t("faq.grade_raw_output", "Technical raw output") }}</summary>
      <p>
        {{
          i18n.t(
            "faq.grade_raw_output_help",
            "Raw grader output is retained for auditability and debugging.",
          )
        }}
      </p>
      <pre>{{ formatJson(rawOutput) }}</pre>
    </details>
  </section>
</template>

<style scoped>
.evaluation-report {
  display: grid;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: linear-gradient(180deg, var(--card), var(--card));
  color: var(--text-2);
}
.evaluation-report-hero {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.evaluation-score {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: baseline;
  justify-content: center;
  padding-top: 15px;
  border: 1px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 28%, var(--line));
  border-radius: 16px;
  background: var(--ui-accent-soft, #edf7f0);
  color: var(--accent-fg);
}
.evaluation-score strong {
  font-size: 1.6875rem;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.evaluation-score span {
  font-size: 0.8125rem;
  font-weight: 800;
}
.evaluation-kicker {
  display: block;
  margin-bottom: 3px;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.evaluation-report-hero h3 {
  margin: 0;
  color: var(--text-2);
  font-size: 0.9375rem;
  line-height: 1.4;
}
.evaluation-report-hero p {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.55;
}
.evaluation-categories {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.evaluation-category {
  display: grid;
  gap: 7px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.evaluation-category-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.evaluation-category-head strong {
  color: var(--text-2);
  font-size: 0.8125rem;
}
.evaluation-category-head span {
  color: var(--accent-fg);
  font-size: 0.875rem;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}
.evaluation-category-head small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.evaluation-meter {
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--soft);
}
.evaluation-meter i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ui-accent, #3c8d62);
}
.evaluation-category p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.evaluation-findings {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.evaluation-finding {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.evaluation-finding header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-2);
}
.evaluation-finding header :deep(svg) {
  width: 14px;
  height: 14px;
}
.evaluation-finding h4 {
  margin: 0;
  font-size: 0.8125rem;
}
.evaluation-finding ul {
  margin: 7px 0 0;
  padding-inline-start: 18px;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.evaluation-finding.positive {
  border-color: var(--line);
}
.evaluation-finding.positive header {
  color: var(--accent-fg);
}
.evaluation-finding.risk {
  border-color: var(--tone-warn-edge);
  background: var(--tone-warn-bg);
}
.evaluation-finding.risk header {
  color: var(--tone-warn-fg);
}
.evaluation-raw {
  border-top: 1px solid var(--line);
  padding-top: 7px;
}
.evaluation-raw > summary {
  width: max-content;
  max-width: 100%;
  min-height: 32px;
  display: flex;
  align-items: center;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
}
.evaluation-raw > p {
  margin: 0 0 7px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.evaluation-raw pre {
  max-height: 320px;
  margin: 0;
  overflow: auto;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--text-2);
  font:
    12px/1.55 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
}
.evaluation-report :is(summary):focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
@media (max-width: 840px) {
  .evaluation-findings {
    grid-template-columns: 1fr;
  }
  .evaluation-categories {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 520px) {
  .evaluation-report-hero {
    grid-template-columns: 1fr;
  }
  .evaluation-score {
    width: 64px;
    height: 64px;
    padding-top: 12px;
  }
}
</style>

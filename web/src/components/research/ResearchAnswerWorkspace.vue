<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchDraftState } from "../../features/research/useResearchDraft";
import type { ResearchJob, ResearchResult } from "../../types/research";
import ResearchClaimReviewPanel from "./ResearchClaimReviewPanel.vue";
import { researchJobDetail } from "./researchI18n";
import { parseResearchAnswer, segmentResearchAnswer } from "./researchAnswerFormatting";

const props = withDefaults(
  defineProps<{
    job?: ResearchJob | null;
    result?: ResearchResult | null;
    /** A streamed, unverified draft of the running job's answer (see useResearchDraft). */
    draft?: ResearchDraftState | null;
    busy?: boolean;
    canGrade?: boolean;
  }>(),
  { job: null, result: null, draft: null, busy: false, canGrade: true },
);
const emit = defineEmits<{
  copy: [];
  grade: [];
  rerun: [];
  details: [];
  evidence: [index: number];
}>();
const i18n = useI18nStore();
const answerBlocks = computed(() =>
  parseResearchAnswer(String(props.result?.answer || ""), i18n.t("research.works_cited")),
);

function citedSegments(value: string) {
  return segmentResearchAnswer(value, props.result?.evidence || []);
}
const runDetail = computed(() =>
  props.job
    ? researchJobDetail(props.job, (key, fallback) => i18n.t(key, fallback), i18n.locale)
    : "",
);
const statusLabel = computed(() => {
  if (!props.job) return "";
  if (props.job.status === "completed") return i18n.t("research.complete");
  if (props.job.status === "failed") return i18n.t("research.failed");
  if (props.job.status === "cancelled") return i18n.t("research.cancelled");
  if (props.job.status === "queued") return i18n.t("research.queued");
  return i18n.t("research.running");
});
</script>

<template>
  <section class="research-answer-workspace card" aria-live="polite">
    <template v-if="result?.answer">
      <header class="research-answer-heading">
        <div>
          <span class="research-answer-kicker">{{ i18n.t("research.answer") }}</span>
          <h2>{{ result.prompt || job?.prompt || i18n.t("research.answer") }}</h2>
          <p>
            {{ result.provider || job?.provider }} · {{ result.model || job?.model
            }}<template v-if="result.elapsed_seconds">
              · {{ Number(result.elapsed_seconds).toFixed(2) }}s</template
            >
          </p>
        </div>
        <div class="research-answer-actions">
          <button class="btn" type="button" @click="emit('copy')">
            <AppIcon name="copy" />{{ i18n.t("research.copy_answer") }}
          </button>
          <button v-if="canGrade" class="btn" type="button" @click="emit('grade')">
            <AppIcon name="spark" />{{ i18n.t("research.grade") }}
          </button>
          <button class="btn" type="button" @click="emit('details')">
            <AppIcon name="history" />{{ i18n.t("research.run_details") }}
          </button>
        </div>
      </header>
      <div v-if="result.warnings?.length" class="research-answer-warning" role="status">
        <p v-for="warning in result.warnings" :key="warning">{{ warning }}</p>
      </div>
      <article class="research-answer-prose">
        <template v-for="(block, index) in answerBlocks" :key="index">
          <h3 v-if="block.kind === 'heading'">{{ block.text }}</h3>
          <ol v-else-if="block.kind === 'ordered'">
            <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
              <template v-for="(segment, segmentIndex) in citedSegments(item)" :key="segmentIndex"
                ><button
                  v-if="segment.evidenceIndex != null"
                  class="research-inline-citation"
                  type="button"
                  :aria-label="`${i18n.t('research.inspect_evidence')} ${segment.text}`"
                  @click="emit('evidence', segment.evidenceIndex)"
                >
                  {{ segment.text }}</button
                ><strong v-else-if="segment.bold">{{ segment.text }}</strong
                ><template v-else>{{ segment.text }}</template></template
              >
            </li>
          </ol>
          <ul v-else-if="block.kind === 'unordered'">
            <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
              <template v-for="(segment, segmentIndex) in citedSegments(item)" :key="segmentIndex"
                ><button
                  v-if="segment.evidenceIndex != null"
                  class="research-inline-citation"
                  type="button"
                  :aria-label="`${i18n.t('research.inspect_evidence')} ${segment.text}`"
                  @click="emit('evidence', segment.evidenceIndex)"
                >
                  {{ segment.text }}</button
                ><strong v-else-if="segment.bold">{{ segment.text }}</strong
                ><template v-else>{{ segment.text }}</template></template
              >
            </li>
          </ul>
          <p v-else>
            <template
              v-for="(segment, segmentIndex) in citedSegments(block.text || '')"
              :key="segmentIndex"
              ><button
                v-if="segment.evidenceIndex != null"
                class="research-inline-citation"
                type="button"
                :aria-label="`${i18n.t('research.inspect_evidence')} ${segment.text}`"
                @click="emit('evidence', segment.evidenceIndex)"
              >
                {{ segment.text }}</button
              ><strong v-else-if="segment.bold">{{ segment.text }}</strong
              ><template v-else>{{ segment.text }}</template></template
            >
          </p>
        </template>
      </article>
      <ResearchClaimReviewPanel
        v-if="result.claim_provenance?.claims?.length"
        :provenance="result.claim_provenance"
        :evidence="result.evidence || []"
        @evidence="emit('evidence', $event)"
      />
      <footer class="research-answer-footer">
        <span>{{ result.evidence?.length || 0 }} {{ i18n.t("research.evidence_records") }}</span>
        <span v-if="result.response_cache?.record_id">{{ i18n.t("research.cached") }}</span>
        <button class="research-text-action" type="button" @click="emit('rerun')">
          {{ i18n.t("research.rerun") }}
        </button>
      </footer>
    </template>

    <template v-else-if="job">
      <div class="research-run-state" :class="job.status">
        <div class="research-run-orb" aria-hidden="true"><span></span></div>
        <div>
          <span class="research-answer-kicker">{{ statusLabel }}</span>
          <h2>
            {{ job.prompt || i18n.t("research.research_in_progress") }}
          </h2>
          <p>{{ runDetail }}</p>
        </div>
      </div>
      <div v-if="job.status === 'failed'" class="research-answer-warning danger" role="alert">
        {{ job.fatal_error || i18n.t("research.run_failed") }}
      </div>
      <div
        v-else-if="draft?.text && draft.jobId === job.id"
        class="research-draft-pane"
        aria-live="polite"
      >
        <span class="research-answer-kicker">{{ i18n.t("research.draft_heading") }}</span>
        <p class="research-draft-text">{{ draft.text }}</p>
        <p class="research-draft-help">{{ i18n.t("research.draft_help") }}</p>
      </div>
    </template>

    <template v-else>
      <div class="research-answer-empty">
        <div aria-hidden="true">∴</div>
        <h2>{{ i18n.t("research.answer_waiting") }}</h2>
        <p>
          {{ i18n.t("research.answer_waiting_help") }}
        </p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.research-answer-kicker {
  display: block;
  margin-bottom: 3px;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.research-answer-prose {
  max-width: min(78ch, 100%);
  padding: 30px 36px 38px;
  color: var(--text);
  font-family: var(--font-reading);
  font-size: 1rem;
  font-weight: var(--fw-regular);
  line-height: 1.74;
  font-variant-ligatures: common-ligatures;
  text-rendering: optimizeLegibility;
}
.research-answer-prose p {
  margin: 0 0 1.28em;
}
.research-answer-prose strong {
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  font-weight: var(--fw-bold);
}
.research-answer-prose h3 {
  margin: 1.8em 0 0.55em;
  font:
    700 15px/1.3 system-ui,
    -apple-system,
    "Segoe UI",
    sans-serif;
  color: var(--text);
}
.research-draft-pane {
  max-width: 700px;
  margin: 0 auto 28px;
  padding: 16px 20px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.research-draft-text {
  margin: 6px 0 8px;
  color: var(--text);
  font:
    14px/1.6 Georgia,
    "Times New Roman",
    serif;
  white-space: pre-line;
}
.research-draft-help {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
}
.research-run-state {
  min-height: 430px;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  align-content: center;
  align-items: center;
  justify-content: center;
  gap: 14px;
  max-width: 700px;
  margin: auto;
  padding: 44px;
}
.research-run-state h2 {
  margin: 2px 0 4px;
  font-size: 1.125rem;
}
.research-run-state p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.research-run-orb {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--ui-accent-soft);
}
.research-run-orb span {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: var(--ui-accent);
  animation: research-pulse 1.4s ease-in-out infinite;
}
@media (max-width: 860px) {
  .research-answer-prose {
    padding: 23px 22px 30px;
  }
}
@media (max-width: 560px) {
  .research-answer-prose {
    font-size: 0.9375rem;
    line-height: 1.7;
    padding: 20px 17px 27px;
  }
}
.research-answer-prose ol,
.research-answer-prose ul {
  margin: 0 0 1.35em;
  padding-left: 1.55em;
}
.research-answer-prose li {
  margin: 0.38em 0;
  padding-left: 0.16em;
}
.research-answer-prose li::marker {
  color: var(--muted);
  font-family:
    system-ui,
    -apple-system,
    "Segoe UI",
    sans-serif;
  font-size: 0.85em;
  font-weight: 700;
}
.research-inline-citation {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  margin: 0 0.08em;
  padding: 0 0.28em;
  border: 0;
  border-radius: 5px;
  background: var(--ui-accent-soft);
  color: var(--accent-fg);
  font: inherit;
  font-family: inherit;
  font-size: 0.94em;
  font-weight: var(--fw-semibold);
  line-height: 1.25;
  vertical-align: 0.02em;
  cursor: pointer;
}
.research-inline-citation:hover {
  box-shadow: inset 0 0 0 1px var(--ui-accent-border);
}
.research-inline-citation:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
@media (prefers-reduced-motion: reduce) {
  .research-run-orb span {
    animation: none;
  }
}
</style>

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
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchDraftState } from "../../features/research/useResearchDraft";
import type { ResearchJob, ResearchResult } from "../../types/research";
import ResearchClaimReviewPanel from "./ResearchClaimReviewPanel.vue";
import { researchJobDetail } from "./researchI18n";
import ResearchAnswerContent from "./ResearchAnswerContent.vue";

const props = withDefaults(
  defineProps<{
    job?: ResearchJob | null;
    result?: ResearchResult | null;
    /** A streamed, unverified draft of the running job's answer (see useResearchDraft). */
    draft?: ResearchDraftState | null;
    busy?: boolean;
    canGrade?: boolean;
    readOnly?: boolean;
    instanceId?: string;
    contextLabel?: string;
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
          <component :is="readOnly ? 'h5' : 'h2'">{{
            result.prompt || job?.prompt || i18n.t("research.answer")
          }}</component>
          <p>
            {{ result.provider || job?.provider }} · {{ result.model || job?.model
            }}<template v-if="result.elapsed_seconds">
              · {{ Number(result.elapsed_seconds).toFixed(2) }}s</template
            >
          </p>
        </div>
        <div v-if="!readOnly" class="research-answer-actions">
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
      <ResearchAnswerContent
        :answer="result.answer"
        :evidence="result.evidence || []"
        :read-only="readOnly"
        @evidence="emit('evidence', $event)"
      />
      <ResearchClaimReviewPanel
        v-if="result.claim_provenance?.claims?.length"
        :provenance="result.claim_provenance"
        :nested="readOnly"
        :heading-id="instanceId ? `${instanceId}-claims` : 'research-claim-review-title'"
        :context-label="contextLabel"
        :evidence="result.evidence || []"
        @evidence="emit('evidence', $event)"
      />
      <footer class="research-answer-footer">
        <span>{{ result.evidence?.length || 0 }} {{ i18n.t("research.evidence_records") }}</span>
        <span v-if="result.response_cache?.record_id">{{ i18n.t("research.cached") }}</span>
        <button v-if="!readOnly" class="research-text-action" type="button" @click="emit('rerun')">
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
  font-family: var(--font-reading);
  font-size: var(--fs-base);
  line-height: 1.6;
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
@media (prefers-reduced-motion: reduce) {
  .research-run-orb span {
    animation: none;
  }
}
</style>

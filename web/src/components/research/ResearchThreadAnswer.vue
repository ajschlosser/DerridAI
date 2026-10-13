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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRef, watch } from "vue";
import { useResearchDraft } from "../../features/research/useResearchDraft";
import { useResearchTurnResult } from "../../features/research/useResearchTurnResult";
import { useAuthStore } from "../../stores/auth";
import { useI18nStore } from "../../stores/i18n";
import ResearchTurnInspector from "./ResearchTurnInspector.vue";
import ResearchAnswerContent from "./ResearchAnswerContent.vue";
import type { ResearchResultEvidence } from "../../types/research";
import type { ResearchTurn } from "../../types/researchThreads";

const props = withDefaults(
  defineProps<{
    turn: ResearchTurn;
    streamLive?: boolean;
    inspectRequested?: boolean;
    inspectorOpen?: boolean;
    deferLoad?: boolean;
  }>(),
  {
    streamLive: true,
    inspectRequested: false,
    inspectorOpen: false,
    deferLoad: false,
  },
);
const emit = defineEmits<{
  openRecord: [item: ResearchResultEvidence];
  openRelationships: [item: ResearchResultEvidence, mode: "trace" | "model"];
  inspect: [turnId: string];
  closeInspector: [turnId: string];
  followUp: [turn: ResearchTurn, evidence: ResearchResultEvidence | null];
}>();
const activeEvidenceIndex = ref(0);
const inspectorRegion = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
const answerRegion = ref<HTMLElement | null>(null);
const visible = ref(!props.deferLoad || typeof IntersectionObserver === "undefined");
let visibilityObserver: IntersectionObserver | null = null;
// Load the selected run immediately; hydrate historical runs as they approach the viewport.
onMounted(() => {
  if (visible.value || !answerRegion.value) return;
  visibilityObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        visible.value = true;
        visibilityObserver?.disconnect();
        visibilityObserver = null;
      }
    },
    { rootMargin: "480px 0px" },
  );
  visibilityObserver.observe(answerRegion.value);
});
onBeforeUnmount(() => visibilityObserver?.disconnect());
const auth = useAuthStore();
const i18n = useI18nStore();
const allowed = computed(() => Boolean(auth.user && auth.can("rag.run")));
const stream = useResearchDraft();
const live = computed(
  () =>
    allowed.value &&
    Boolean(props.turn.job_id) &&
    ["queued", "running"].includes(props.turn.status),
);
const streamLive = computed(() => live.value && props.streamLive);
// A retry starts a new stream. Scope changes drop advisory text synchronously.
watch(
  () => [
    auth.user?.id,
    auth.user?.role,
    allowed.value,
    props.turn.thread_id,
    props.turn.turn_id,
    props.turn.job_id,
    props.turn.attempt,
    streamLive.value,
  ],
  () => {
    stream.clear();
    activeEvidenceIndex.value = 0;
    if (streamLive.value) stream.follow(props.turn.job_id!);
  },
  { immediate: true, flush: "sync" },
);
onBeforeUnmount(stream.clear);
const { answer, denied, result } = useResearchTurnResult(
  toRef(props, "turn"),
  computed(() => visible.value || props.inspectRequested),
);
function openRecord(index: number) {
  const item = result.value?.evidence?.[index];
  if (item) emit("openRecord", item);
}
function followUpPassage(index: number) {
  emit("followUp", props.turn, result.value?.evidence?.[index] ?? null);
}
function openRelationships(index: number, mode: "trace" | "model") {
  const item = result.value?.evidence?.[index];
  if (item) emit("openRelationships", item, mode);
}
function inspectCitation(index: number) {
  if (!allowed.value || !result.value?.evidence?.[index]) return;
  activeEvidenceIndex.value = index;
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  emit("inspect", props.turn.turn_id);
  void nextTick(() => inspectorRegion.value?.focus({ preventScroll: true }));
}
function toggleInspector() {
  if (props.inspectorOpen) {
    closeInspector();
    return;
  }
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  emit("inspect", props.turn.turn_id);
  void nextTick(() => inspectorRegion.value?.focus({ preventScroll: true }));
}
function closeInspector() {
  emit("closeInspector", props.turn.turn_id);
  const focus = previousFocus;
  previousFocus = null;
  void nextTick(() => {
    if (focus?.isConnected) focus.focus({ preventScroll: true });
  });
}
watch(
  () => [
    props.turn.thread_id,
    props.turn.turn_id,
    props.turn.attempt,
    props.turn.job_id,
    allowed.value,
  ],
  () => {
    activeEvidenceIndex.value = 0;
    previousFocus = null;
  },
  { flush: "sync" },
);
</script>
<template>
  <section
    ref="answerRegion"
    v-if="
      allowed &&
      (turn.job_id || turn.response_record_id) &&
      (streamLive || turn.status === 'completed')
    "
    :aria-label="`${i18n.t('research.answer')} ${turn.ordinal}: ${turn.user_question}`"
  >
    <template v-if="streamLive">
      <p role="status">{{ i18n.t("research.draft_heading") }}</p>
      <p>{{ i18n.t("research.draft_help") }}</p>
      <p class="thread-answer-draft">{{ stream.draft.value?.text }}</p>
    </template>
    <template v-else>
      <p v-if="!visible && !inspectRequested" role="status">
        {{ i18n.t("loading.updating") }}
      </p>
      <p v-if="answer.isFetching.value" role="status">{{ i18n.t("loading.updating") }}</p>
      <div v-if="answer.error.value" role="alert">
        <p>
          {{ denied ? i18n.t("research.thread_run_unavailable") : String(answer.error.value) }}
        </p>
        <button class="btn" type="button" @click="answer.refetch()">
          {{ i18n.t("ui.retry") }}
        </button>
      </div>
      <div v-if="result?.answer" class="thread-answer-workspace">
        <ResearchAnswerContent
          :answer="result.answer"
          :evidence="result.evidence || []"
          compact
          read-only
          @evidence="inspectCitation"
        />
        <details v-if="result.evidence?.length">
          <summary>{{ i18n.t("research.works_cited") }}</summary>
          <ul>
            <li v-for="(item, index) in result.evidence" :key="item.evidence_id || index">
              {{ item.full_citation || item.inline_citation || item.evidence_id }}
            </li>
          </ul>
        </details>
        <button
          type="button"
          class="btn thread-answer-inspect-toggle"
          :aria-expanded="inspectorOpen"
          :aria-controls="inspectorOpen ? `thread-answer-${turn.turn_id}-inspector` : undefined"
          @click="toggleInspector"
        >
          {{ i18n.t("research.thread_inspect_result") }}
        </button>
        <div
          v-if="inspectorOpen"
          :id="`thread-answer-${turn.turn_id}-inspector`"
          ref="inspectorRegion"
          class="thread-answer-inspector"
          tabindex="-1"
          @keydown.esc.stop="closeInspector"
        >
          <ResearchTurnInspector
            :instance-id="`thread-answer-${turn.turn_id}`"
            :context-label="`${turn.ordinal}: ${turn.user_question}`"
            :job="answer.data.value"
            :result="result"
            :active-evidence-index="activeEvidenceIndex"
            :researcher="!auth.isAdmin"
            @close="closeInspector"
            @select-evidence="activeEvidenceIndex = $event"
            @open-record="openRecord"
            @open-relationships="openRelationships"
            @follow-up="followUpPassage"
          />
        </div>
      </div>
      <p
        v-else-if="(visible || inspectRequested) && !answer.isFetching.value && !answer.error.value"
      >
        {{ i18n.t("research.thread_run_unavailable") }}
      </p>
    </template>
  </section>
</template>
<style scoped>
.thread-answer-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  min-width: 0;
}
.thread-answer-draft {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.65;
  max-width: 78ch;
  margin-block: 0;
}
.thread-answer-workspace > details {
  min-width: 0;
}
.thread-answer-workspace > details summary {
  cursor: pointer;
  padding: 8px 0;
}
.thread-answer-inspect-toggle {
  justify-self: start;
  /* Wrap the label instead of overflowing a 320px viewport. */
  max-width: 100%;
  white-space: normal;
  text-align: start;
}
.thread-answer-inspector {
  min-width: 0;
  outline-offset: 3px;
}
@media (min-width: 1280px) {
  .thread-answer-workspace:has(.thread-answer-inspector) {
    grid-template-columns: minmax(0, 1fr) minmax(310px, 42%);
  }
  .thread-answer-workspace:has(.thread-answer-inspector) > .thread-answer-text {
    grid-column: 1;
    grid-row: 1 / span 2;
  }
  .thread-answer-workspace:has(.thread-answer-inspector) > .thread-answer-inspector {
    grid-column: 2;
    grid-row: 1 / span 3;
    max-height: min(70dvh, 850px);
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .thread-answer-workspace:has(.thread-answer-inspector) > details {
    grid-column: 1;
  }
}
@media (max-width: 600px) {
  .thread-answer-inspector {
    position: fixed;
    inset-inline: 0;
    bottom: 0;
    z-index: 30;
    max-height: 74dvh;
    overflow: auto;
    padding: 12px;
    background: var(--surface-card);
    border-top: 1px solid var(--border);
    box-shadow: 0 -8px 28px rgb(0 0 0 / 0.18);
    overscroll-behavior: contain;
  }
}
</style>

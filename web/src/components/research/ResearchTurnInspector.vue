<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchJob, ResearchResult } from "../../types/research";
import ResearchEvidencePanel from "./ResearchEvidencePanel.vue";
import ResearchClaimReviewPanel from "./ResearchClaimReviewPanel.vue";
import ResearchEvidenceProvenance from "./ResearchEvidenceProvenance.vue";

type InspectorSection = "sources" | "claims" | "run";

const props = withDefaults(
  defineProps<{
    result: ResearchResult;
    job?: ResearchJob | null;
    activeEvidenceIndex?: number;
    instanceId: string;
    contextLabel?: string;
    researcher?: boolean;
  }>(),
  { job: null, activeEvidenceIndex: 0, contextLabel: "", researcher: false },
);
const emit = defineEmits<{
  close: [];
  selectEvidence: [index: number];
  openRecord: [index: number];
  openRelationships: [index: number, mode: "trace" | "model"];
  followUp: [index: number];
}>();
const i18n = useI18nStore();
const section = ref<InspectorSection>("sources");
const activeEvidence = computed(() => props.result.evidence?.[props.activeEvidenceIndex] ?? null);
const hasClaims = computed(() => Boolean(props.result.claim_provenance?.claims?.length));

watch(
  () => props.activeEvidenceIndex,
  () => {
    // A citation always reveals its own turn's documentary passage.
    section.value = "sources";
  },
);

const options = computed(() => [
  { value: "sources" as const, label: i18n.t("research.answer_evidence") },
  { value: "claims" as const, label: i18n.t("research.claim_review_title") },
  { value: "run" as const, label: i18n.t("research.run_details") },
]);
function setSection(next: InspectorSection) {
  section.value = next;
}
</script>

<template>
  <section
    class="research-turn-inspector"
    :aria-label="`${i18n.t('research.thread_inspect_result')} ${contextLabel}`"
  >
    <header class="research-turn-inspector-header">
      <h4>{{ i18n.t("research.thread_inspect_result") }}</h4>
      <button type="button" class="btn" @click="emit('close')">
        {{ i18n.t("ui.close") }}
      </button>
    </header>
    <div
      class="research-turn-inspector-sections"
      role="group"
      :aria-label="i18n.t('research.thread_inspect_result')"
    >
      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        class="research-turn-inspector-section"
        :aria-pressed="section === option.value"
        :aria-controls="`${instanceId}-${option.value}`"
        @click="setSection(option.value)"
      >
        {{ option.label }}
      </button>
    </div>
    <div v-show="section === 'sources'" :id="`${instanceId}-sources`">
      <ResearchEvidencePanel
        v-if="result.evidence?.length"
        :panel-id="`${instanceId}-evidence`"
        :context-label="contextLabel"
        :result-evidence="result.evidence"
        :answer="result.answer || ''"
        :active-index="activeEvidenceIndex"
        :researcher="researcher"
        @select="emit('selectEvidence', $event)"
        @open-record="emit('openRecord', $event)"
        @open-relationships="(index, mode) => emit('openRelationships', index, mode)"
      />
      <p v-else>{{ i18n.t("research.no_evidence_text") }}</p>
      <ResearchEvidenceProvenance
        v-if="activeEvidence"
        :evidence="activeEvidence"
        :provenance="result.claim_provenance"
      />
      <button
        v-if="activeEvidence"
        type="button"
        class="btn research-turn-inspector-follow-up"
        @click="emit('followUp', activeEvidenceIndex)"
      >
        {{ i18n.t("research.thread_follow_up_passage") }}
      </button>
    </div>
    <div v-show="section === 'claims'" :id="`${instanceId}-claims`">
      <ResearchClaimReviewPanel
        v-if="section === 'claims' && hasClaims"
        :provenance="result.claim_provenance"
        :evidence="result.evidence || []"
        nested
        :heading-id="`${instanceId}-claim-heading`"
        :context-label="contextLabel"
        @evidence="
          emit('selectEvidence', $event);
          section = 'sources';
        "
      />
      <p v-else>{{ i18n.t("ui.none") }}</p>
    </div>
    <div v-show="section === 'run'" :id="`${instanceId}-run`" class="research-turn-inspector-audit">
      <dl>
        <template v-if="job?.id">
          <dt>{{ i18n.t("research.run_details") }}</dt>
          <dd>{{ job.id }}</dd>
        </template>
        <template v-if="result.provider">
          <dt>{{ i18n.t("research.provider") }}</dt>
          <dd>{{ result.provider }}</dd>
        </template>
        <template v-if="result.model">
          <dt>{{ i18n.t("research.model") }}</dt>
          <dd>{{ result.model }}</dd>
        </template>
        <template v-if="result.elapsed_seconds != null">
          <dt>{{ i18n.t("faq.elapsed") }}</dt>
          <dd>{{ result.elapsed_seconds }}</dd>
        </template>
      </dl>
      <div v-if="result.warnings?.length" role="status">
        <p v-for="warning in result.warnings" :key="warning">{{ warning }}</p>
      </div>
      <details v-if="result.research_thread">
        <summary>{{ i18n.t("research.thread_context_audit") }}</summary>
        <pre>{{ JSON.stringify(result.research_thread, null, 2) }}</pre>
      </details>
    </div>
  </section>
</template>

<style scoped>
.research-turn-inspector {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  padding: clamp(12px, 1.5vw, 20px);
}
.research-turn-inspector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.research-turn-inspector-header h4 {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.4;
}
.research-turn-inspector-sections {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 14px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.research-turn-inspector-section {
  padding: 8px 12px;
  min-height: 38px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--surface-card);
  color: var(--text-primary);
  cursor: pointer;
}
.research-turn-inspector-section[aria-pressed="true"] {
  color: var(--accent-fg);
  background: var(--soft);
  border-color: var(--accent-fg);
  font-weight: 700;
}
.research-turn-inspector-section:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
.research-turn-inspector :deep(.research-evidence-panel) {
  max-width: none;
  box-shadow: none;
}
.research-turn-inspector-audit {
  overflow-wrap: anywhere;
}
.research-turn-inspector-audit dl {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 8px 16px;
}
.research-turn-inspector-audit dt {
  color: var(--text-tertiary);
}
.research-turn-inspector-audit dd {
  margin: 0;
}
.research-turn-inspector-audit pre {
  max-width: 100%;
  overflow-x: auto;
}
</style>

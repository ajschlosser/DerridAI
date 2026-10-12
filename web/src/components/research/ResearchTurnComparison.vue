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
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchTurn } from "../../types/researchThreads";
import { useResearchTurnResult } from "../../features/research/useResearchTurnResult";
import {
  claimStatusCounts,
  compareTurnEvidence,
} from "../../features/research/researchTurnComparison";
import ResearchAnswerContent from "./ResearchAnswerContent.vue";

// Compares two completed turns of one thread. Each side loads its own exact
// attempt; evidence is aligned by Record without merging run identity.
const props = defineProps<{ turns: ResearchTurn[] }>();
const emit = defineEmits<{ close: [] }>();
const i18n = useI18nStore();
const completed = computed(() => props.turns.filter((turn) => turn.status === "completed"));
const leftId = ref("");
const rightId = ref("");
watch(
  completed,
  (turns) => {
    const ids = turns.map((turn) => turn.turn_id);
    if (!ids.includes(leftId.value)) leftId.value = ids[ids.length - 2] || "";
    if (!ids.includes(rightId.value)) rightId.value = ids[ids.length - 1] || "";
  },
  { immediate: true },
);
const empty = { turn_id: "", thread_id: "", status: "failed" } as unknown as ResearchTurn;
const leftTurn = computed(
  () => completed.value.find((turn) => turn.turn_id === leftId.value) || empty,
);
const rightTurn = computed(
  () => completed.value.find((turn) => turn.turn_id === rightId.value) || empty,
);
const distinct = computed(() =>
  Boolean(leftId.value && rightId.value && leftId.value !== rightId.value),
);
const left = useResearchTurnResult(leftTurn, distinct);
const right = useResearchTurnResult(rightTurn, distinct);
const sides = computed(() => [
  { key: "left", turn: leftTurn.value, state: left },
  { key: "right", turn: rightTurn.value, state: right },
]);
const passages = computed(() => compareTurnEvidence(left.result.value, right.result.value));
function claims(side: (typeof sides.value)[number]) {
  return Object.entries(claimStatusCounts(side.state.result.value));
}
function presence(row: (typeof passages.value)[number]) {
  if (!row.recordId) return i18n.t("research.compare_no_record_id");
  if (row.left && row.right)
    return i18n.t(
      row.revisionDiffers ? "research.compare_revision_differs" : "research.compare_in_both",
    );
  return i18n.tf("research.compare_only_in", {
    ordinal: (row.left ? leftTurn.value : rightTurn.value).ordinal,
  });
}
function cited(item: (typeof passages.value)[number]["left"], revision: number | null) {
  if (!item) return "—";
  const label = item.inline_citation || item.evidence_id || "";
  return revision === null
    ? label
    : `${label} (${i18n.tf("research.compare_revision", { revision })})`;
}
</script>

<template>
  <section class="research-turn-comparison" aria-labelledby="research-turn-comparison-title">
    <header>
      <h3 id="research-turn-comparison-title">{{ i18n.t("research.compare_turns") }}</h3>
      <button type="button" class="btn" @click="emit('close')">{{ i18n.t("ui.close") }}</button>
    </header>
    <div class="research-turn-comparison-pickers">
      <label>
        {{ i18n.t("research.compare_left") }}
        <select v-model="leftId">
          <option v-for="turn in completed" :key="turn.turn_id" :value="turn.turn_id">
            {{ turn.ordinal }}: {{ turn.user_question }}
          </option>
        </select>
      </label>
      <label>
        {{ i18n.t("research.compare_right") }}
        <select v-model="rightId">
          <option v-for="turn in completed" :key="turn.turn_id" :value="turn.turn_id">
            {{ turn.ordinal }}: {{ turn.user_question }}
          </option>
        </select>
      </label>
    </div>
    <p v-if="!distinct" role="status">{{ i18n.t("research.compare_same") }}</p>
    <template v-else>
      <p class="research-turn-comparison-note">{{ i18n.t("research.compare_note") }}</p>
      <div class="research-turn-comparison-columns">
        <article v-for="side in sides" :key="side.key" :data-side="side.key">
          <h4>
            {{
              i18n.tf("research.context_scope_turn", {
                ordinal: side.turn.ordinal,
                question: side.turn.user_question,
              })
            }}
          </h4>
          <p v-if="side.state.answer.isFetching.value" role="status">
            {{ i18n.t("loading.updating") }}
          </p>
          <p v-else-if="!side.state.result.value">
            {{ i18n.t("research.thread_run_unavailable") }}
          </p>
          <template v-else>
            <dl>
              <dt>{{ i18n.t("research.run_details") }}</dt>
              <dd>{{ side.turn.research_run_id || side.turn.job_id }}</dd>
              <template v-if="side.state.result.value.model">
                <dt>{{ i18n.t("research.model") }}</dt>
                <dd>
                  {{ side.state.result.value.provider }} · {{ side.state.result.value.model }}
                </dd>
              </template>
              <dt>{{ i18n.t("research.claim_review_title") }}</dt>
              <dd>
                <template v-if="claims(side).length">
                  <span v-for="[status, count] in claims(side)" :key="status" :data-status="status">
                    {{ i18n.t(`claims.status_${status}`, status) }}: {{ count }}
                  </span>
                </template>
                <template v-else>{{ i18n.t("ui.none") }}</template>
              </dd>
            </dl>
            <ResearchAnswerContent
              :answer="side.state.result.value.answer || ''"
              :evidence="side.state.result.value.evidence || []"
              compact
              read-only
            />
          </template>
        </article>
      </div>
      <div v-if="passages.length" class="research-turn-comparison-passages">
        <table>
          <caption>
            {{
              i18n.t("research.compare_passages")
            }}
          </caption>
          <thead>
            <tr>
              <th scope="col">{{ i18n.t("research.compare_record") }}</th>
              <th scope="col">{{ leftTurn.ordinal }}</th>
              <th scope="col">{{ rightTurn.ordinal }}</th>
              <th scope="col">{{ i18n.t("research.compare_presence") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, index) in passages"
              :key="`${row.collection}:${row.recordId}:${index}`"
            >
              <th scope="row">{{ row.recordId || "—" }}</th>
              <td>{{ cited(row.left, row.leftRevision) }}</td>
              <td>{{ cited(row.right, row.rightRevision) }}</td>
              <td>{{ presence(row) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.research-turn-comparison {
  display: grid;
  gap: 12px;
  min-width: 0;
  margin-block: 12px;
  padding: clamp(12px, 1.5vw, 20px);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.research-turn-comparison header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.research-turn-comparison h3,
.research-turn-comparison h4 {
  margin: 0;
  overflow-wrap: anywhere;
}
.research-turn-comparison-pickers,
.research-turn-comparison-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: 12px;
}
.research-turn-comparison-pickers label {
  display: grid;
  gap: 4px;
}
.research-turn-comparison-pickers select {
  min-width: 0;
  max-width: 100%;
}
.research-turn-comparison-columns article {
  min-width: 0;
  display: grid;
  gap: 8px;
  align-content: start;
}
.research-turn-comparison dd span {
  display: inline-block;
  margin-inline-end: 8px;
}
.research-turn-comparison-note {
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.research-turn-comparison-passages {
  overflow-x: auto;
}
.research-turn-comparison table {
  width: 100%;
  border-collapse: collapse;
}
.research-turn-comparison caption {
  text-align: start;
  font-weight: 600;
  padding-block-end: 6px;
}
.research-turn-comparison th,
.research-turn-comparison td {
  padding: 6px 8px;
  border-top: 1px solid var(--border);
  text-align: start;
  vertical-align: top;
  overflow-wrap: anywhere;
}
</style>

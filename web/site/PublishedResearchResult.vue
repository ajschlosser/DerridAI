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
import { computed, useId } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import UiCard from "../src/components/ui/UiCard.vue";

type EvidenceItem = {
  evidenceId: string;
  recordId: string;
  work?: string;
  citation?: string;
};

type PublicationRecord = {
  record_id?: string;
  inline_citation?: string;
  full_citation?: string;
  citation?: string;
  work?: string;
};

type AnswerSegment =
  | { kind: "text"; text: string }
  | { kind: "citation"; text: string; evidence: EvidenceItem };

const props = defineProps<{
  answer: string;
  evidence: EvidenceItem[];
  recordsById: Map<string, PublicationRecord>;
  evidenceTarget: HTMLElement;
  evidenceLabel: string;
  openRecordLabel: string;
  onOpenRecord: (recordId: string) => void | Promise<void>;
}>();

const evidenceHeadingId = `${useId()}-published-evidence-heading`;

function evidenceTargetId(evidenceId: string) {
  return `research-evidence-${String(evidenceId || "").replace(/[^A-Za-z0-9_-]+/g, "-")}`;
}

function inlineCitation(item: EvidenceItem) {
  const record = props.recordsById.get(String(item.recordId));
  const inline = String(record?.inline_citation || "").trim();
  if (inline) {
    return inline.startsWith("(") && inline.endsWith(")") ? inline : `(${inline})`;
  }
  const fallback = String(
    item.citation || record?.full_citation || record?.citation || item.work || item.recordId || "",
  ).trim();
  if (!fallback) return `[${item.evidenceId}]`;
  return fallback.startsWith("(") && fallback.endsWith(")") ? fallback : `(${fallback})`;
}

const evidenceById = computed(
  () =>
    new Map(
      props.evidence.map((item) => [String(item.evidenceId || "").toUpperCase(), item] as const),
    ),
);

const answerSegments = computed<AnswerSegment[]>(() => {
  const raw = String(props.answer || "");
  const marker = /\[(E\d+)\]/gi;
  const segments: AnswerSegment[] = [];
  let cursor = 0;

  for (let match = marker.exec(raw); match; match = marker.exec(raw)) {
    if (match.index > cursor) {
      segments.push({ kind: "text", text: raw.slice(cursor, match.index) });
    }
    const item = evidenceById.value.get(match[1].toUpperCase());
    if (item) {
      segments.push({ kind: "citation", text: inlineCitation(item), evidence: item });
    } else {
      segments.push({ kind: "text", text: match[0] });
    }
    cursor = marker.lastIndex;
  }

  if (cursor < raw.length) {
    segments.push({ kind: "text", text: raw.slice(cursor) });
  }
  return segments;
});
</script>

<template>
  <div class="published-research-answer">
    <template v-for="(segment, index) in answerSegments" :key="index">
      <a
        v-if="segment.kind === 'citation'"
        class="inline-citation"
        :data-evidence-id="segment.evidence.evidenceId"
        :href="`#${evidenceTargetId(segment.evidence.evidenceId)}`"
        >{{ segment.text }}</a
      >
      <template v-else>{{ segment.text }}</template>
    </template>
  </div>

  <Teleport :to="evidenceTarget">
    <UiCard class="published-evidence-card" :heading-id="evidenceHeadingId">
      <h3 :id="evidenceHeadingId">{{ evidenceLabel }}</h3>
      <div class="published-evidence-list">
        <div
          v-for="item in evidence"
          :id="evidenceTargetId(item.evidenceId)"
          :key="item.evidenceId"
          class="evidence-item"
          :data-evidence-id="item.evidenceId"
        >
          <UiButton
            :label="openRecordLabel"
            button-class="published-evidence-button"
            @click="onOpenRecord(item.recordId)"
          >
            <span class="published-evidence-copy">
              <strong>[​{{ item.evidenceId }}] {{ item.work || item.recordId }}</strong>
              <small>{{
                item.citation ||
                recordsById.get(String(item.recordId))?.full_citation ||
                recordsById.get(String(item.recordId))?.citation ||
                ""
              }}</small>
            </span>
          </UiButton>
        </div>
      </div>
    </UiCard>
  </Teleport>
</template>

<style scoped>
.published-research-answer {
  white-space: pre-wrap;
}
.inline-citation {
  font-family: inherit;
}
.published-evidence-card {
  align-content: start;
}
.published-evidence-card h3 {
  margin-block-start: 0;
}
.published-evidence-list {
  display: grid;
  gap: 0.6rem;
}
.evidence-item {
  scroll-margin-top: 6rem;
}
.evidence-item:target {
  outline: 3px solid var(--accent);
  outline-offset: 3px;
  border-radius: var(--radius-control, 0.55rem);
}
:deep(.published-evidence-button) {
  width: 100%;
  height: auto;
  justify-content: flex-start;
  text-align: start;
}
.published-evidence-copy {
  display: grid;
  gap: 0.18rem;
  min-width: 0;
}
.published-evidence-copy strong,
.published-evidence-copy small {
  overflow-wrap: anywhere;
}
.published-evidence-copy small {
  color: var(--muted);
  font-weight: 400;
}
</style>

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
import { useI18nStore } from "../../stores/i18n";
import type { ResearchResultEvidence } from "../../types/research";
import {
  citationNumbers,
  compactCitationGroups,
  parseResearchAnswer,
  segmentResearchAnswer,
} from "./researchAnswerFormatting";

const props = withDefaults(
  defineProps<{
    answer: string;
    evidence?: ResearchResultEvidence[];
    /** Keep the thread reading layout without changing citation semantics. */
    compact?: boolean;
    readOnly?: boolean;
    highlightIndex?: number | null;
  }>(),
  { evidence: () => [], compact: false, readOnly: false, highlightIndex: null },
);
const emit = defineEmits<{ evidence: [index: number] }>();
const i18n = useI18nStore();
const blocks = computed(() => parseResearchAnswer(props.answer, i18n.t("research.works_cited")));
const heading = computed(() => (props.compact ? "h4" : props.readOnly ? "h6" : "h3"));

const numbers = computed(() => citationNumbers(blocks.value, props.evidence));

function segments(text: string) {
  // Evidence IDs and inline citations are resolved only against this answer's packet.
  return compactCitationGroups(segmentResearchAnswer(text, props.evidence));
}

function entrySegments(text: string) {
  // Bibliography entries are formatted text, never bound citations.
  return segmentResearchAnswer(text, []);
}

function citationLabel(index: number, citation: string) {
  return `${i18n.t("research.inspect_evidence")} ${numbers.value.get(index) ?? ""}: ${citation}`;
}

function citationTitle(index: number, citation: string) {
  // The MLA in-text form, as plain text, on hover; the source panel shows it formatted.
  return (props.evidence[index]?.mla_in_text || citation).replace(/\*/g, "");
}
</script>

<template>
  <article class="research-answer-prose" :class="{ 'thread-answer-text': compact }">
    <template v-for="(block, index) in blocks" :key="index">
      <component :is="heading" v-if="block.kind === 'heading'">{{ block.text }}</component>
      <ol v-else-if="block.kind === 'ordered'">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
          <template v-for="(segment, segmentIndex) in segments(item)" :key="segmentIndex">
            <button
              v-if="segment.evidenceIndex != null"
              class="research-inline-citation"
              :class="{
                'thread-answer-citation': compact,
                'research-citation-corresponding': segment.evidenceIndex === highlightIndex,
              }"
              type="button"
              :aria-label="citationLabel(segment.evidenceIndex, segment.text)"
              :title="citationTitle(segment.evidenceIndex, segment.text)"
              @click="emit('evidence', segment.evidenceIndex)"
            >
              {{ numbers.get(segment.evidenceIndex) }}
            </button>
            <strong v-else-if="segment.bold"
              ><em v-if="segment.italic">{{ segment.text }}</em
              ><template v-else>{{ segment.text }}</template></strong
            >
            <em v-else-if="segment.italic">{{ segment.text }}</em>
            <template v-else>{{ segment.text }}</template>
          </template>
        </li>
      </ol>
      <ul v-else-if="block.kind === 'unordered'">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
          <template v-for="(segment, segmentIndex) in segments(item)" :key="segmentIndex">
            <button
              v-if="segment.evidenceIndex != null"
              class="research-inline-citation"
              :class="{
                'thread-answer-citation': compact,
                'research-citation-corresponding': segment.evidenceIndex === highlightIndex,
              }"
              type="button"
              :aria-label="citationLabel(segment.evidenceIndex, segment.text)"
              :title="citationTitle(segment.evidenceIndex, segment.text)"
              @click="emit('evidence', segment.evidenceIndex)"
            >
              {{ numbers.get(segment.evidenceIndex) }}
            </button>
            <strong v-else-if="segment.bold"
              ><em v-if="segment.italic">{{ segment.text }}</em
              ><template v-else>{{ segment.text }}</template></strong
            >
            <em v-else-if="segment.italic">{{ segment.text }}</em>
            <template v-else>{{ segment.text }}</template>
          </template>
        </li>
      </ul>
      <ul v-else-if="block.kind === 'works_cited'" class="research-works-cited">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
          <template v-for="(segment, segmentIndex) in entrySegments(item)" :key="segmentIndex">
            <em v-if="segment.italic">{{ segment.text }}</em>
            <template v-else>{{ segment.text }}</template>
          </template>
        </li>
      </ul>
      <p v-else>
        <template v-for="(segment, segmentIndex) in segments(block.text || '')" :key="segmentIndex">
          <button
            v-if="segment.evidenceIndex != null"
            class="research-inline-citation"
            :class="{
              'thread-answer-citation': compact,
              'research-citation-corresponding': segment.evidenceIndex === highlightIndex,
            }"
            type="button"
            :aria-label="citationLabel(segment.evidenceIndex, segment.text)"
            :title="citationTitle(segment.evidenceIndex, segment.text)"
            @click="emit('evidence', segment.evidenceIndex)"
          >
            {{ numbers.get(segment.evidenceIndex) }}
          </button>
          <strong v-else-if="segment.bold"
            ><em v-if="segment.italic">{{ segment.text }}</em
            ><template v-else>{{ segment.text }}</template></strong
          >
          <em v-else-if="segment.italic">{{ segment.text }}</em>
          <template v-else>{{ segment.text }}</template>
        </template>
      </p>
    </template>
  </article>
</template>

<style scoped>
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
  overflow-wrap: anywhere;
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
.research-answer-prose :is(h3, h4, h6) {
  margin: 1.8em 0 0.55em;
  font:
    700 15px/1.3 system-ui,
    -apple-system,
    "Segoe UI",
    sans-serif;
  color: var(--text);
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
  font-size: 0.85em;
  font-weight: 700;
}
.research-inline-citation {
  min-width: 20px;
  min-height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0 0.06em;
  padding: 0 0.3em;
  border: 1px solid var(--ui-accent-border);
  border-radius: 5px;
  background: var(--ui-accent-soft);
  color: var(--accent-fg);
  font-family: var(--font-ui);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  line-height: 1;
  vertical-align: 0.15em;
  cursor: pointer;
}
.research-inline-citation.research-citation-corresponding {
  border-color: var(--accent-fg);
  background: var(--accent-fg);
  color: var(--accent-on);
}
.research-inline-citation:hover {
  box-shadow: inset 0 0 0 1px var(--ui-accent-border);
}
.research-inline-citation:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.research-answer-prose.thread-answer-text {
  max-width: 78ch;
  padding: 0;
  margin: 0;
  font-size: 1rem;
  line-height: 1.65;
}
.research-works-cited {
  margin: 0 0 1.35em;
  padding: 0;
  list-style: none;
}
.research-answer-prose .research-works-cited li {
  margin: 0 0 0.5em;
  /* MLA hanging indent. */
  padding-left: 2em;
  text-indent: -2em;
}
@media (max-width: 860px) {
  .research-answer-prose:not(.thread-answer-text) {
    padding: 23px 22px 30px;
  }
}
@media (max-width: 560px) {
  .research-answer-prose {
    font-size: 0.9375rem;
    line-height: 1.7;
  }
  .research-answer-prose:not(.thread-answer-text) {
    padding: 20px 17px 27px;
  }
}
</style>

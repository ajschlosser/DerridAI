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
import type { SourceBlock } from "../../api/pdfCorpus";
import { timeLabel } from "../../domain/sourceMedia";
import { useI18nStore } from "../../stores/i18n";

defineOptions({ name: "AudioSpeakerTimeline" });

const props = withDefaults(
  defineProps<{
    blocks: SourceBlock[];
    voiceAssignments?: Record<string, string>;
    duration?: number;
  }>(),
  {
    voiceAssignments: () => ({}),
    duration: 0,
  },
);

const emit = defineEmits<{
  seek: [block: SourceBlock];
}>();

const i18n = useI18nStore();

const timedBlocks = computed(() =>
  props.blocks.filter(
    (block) =>
      typeof block.start === "number" && typeof block.end === "number" && block.end > block.start,
  ),
);

const timelineEnd = computed(() =>
  Math.max(props.duration || 0, ...timedBlocks.value.map((block) => Number(block.end) || 0), 0.001),
);

const rows = computed(() => {
  const grouped = new Map<string, SourceBlock[]>();
  for (const block of timedBlocks.value) {
    const voice = String(block.speaker || "").trim() || "unassigned";
    const existing = grouped.get(voice) || [];
    existing.push(block);
    grouped.set(voice, existing);
  }
  return Array.from(grouped.entries()).map(([voice, blocks]) => ({
    voice,
    label:
      voice === "unassigned"
        ? i18n.t("pdf_corpus.audio_unassigned_speaker", "Unassigned speaker")
        : props.voiceAssignments[voice] || voice,
    blocks,
  }));
});

function segmentStyle(block: SourceBlock) {
  const duration = timelineEnd.value;
  const start = Math.max(0, Number(block.start) || 0);
  const end = Math.max(start, Number(block.end) || start);
  return {
    insetInlineStart: `${Math.min(100, (start / duration) * 100)}%`,
    inlineSize: `${Math.max(0.8, Math.min(100, ((end - start) / duration) * 100))}%`,
  };
}
</script>

<template>
  <section
    v-if="rows.length"
    class="speaker-timeline"
    :aria-label="i18n.t('pdf_corpus.audio_speaker_timeline', 'Speaker timeline')"
  >
    <header>
      <strong>{{ i18n.t("pdf_corpus.audio_speaker_timeline", "Speaker timeline") }}</strong>
      <small>{{
        i18n.t(
          "pdf_corpus.audio_speaker_timeline_help",
          "Select a timed turn to seek the recording to that evidence.",
        )
      }}</small>
    </header>
    <div class="timeline-rows">
      <div v-for="row in rows" :key="row.voice" class="timeline-row">
        <span class="timeline-speaker">{{ row.label }}</span>
        <div class="timeline-track">
          <button
            v-for="block in row.blocks"
            :key="block.block_id"
            type="button"
            class="timeline-segment"
            :class="{ 'needs-review': block.speaker_assignment?.review_recommended }"
            :style="segmentStyle(block)"
            :aria-label="`${row.label}: ${timeLabel(block.start, block.end)}`"
            :title="`${row.label} · ${timeLabel(block.start, block.end)}`"
            @click="emit('seek', block)"
          >
            <span class="sr-only">{{ block.text }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.speaker-timeline {
  display: grid;
  gap: var(--space-3, 12px);
  padding: var(--space-3, 12px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}

.speaker-timeline header {
  display: grid;
  gap: 2px;
}

.speaker-timeline small {
  color: var(--text-tertiary);
}

.timeline-rows {
  display: grid;
  gap: var(--space-2, 8px);
}

.timeline-row {
  display: grid;
  grid-template-columns: minmax(7rem, 10rem) minmax(0, 1fr);
  gap: var(--space-2, 8px);
  align-items: center;
}

.timeline-speaker {
  overflow: hidden;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-track {
  position: relative;
  min-block-size: 28px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  overflow: hidden;
}

.timeline-segment {
  position: absolute;
  inset-block: 3px;
  min-inline-size: 6px;
  padding: 0;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-control);
  background: var(--surface-selected);
  cursor: pointer;
}

.timeline-segment:hover {
  background: var(--surface-hover);
}

.timeline-segment.needs-review {
  border-color: var(--tone-warn-edge);
  background: var(--tone-warn-bg);
}

.timeline-segment:focus-visible {
  outline: var(--focus-ring-width) solid var(--accent);
  outline-offset: calc(-1 * var(--focus-ring-offset));
}

@media (max-width: 700px) {
  .timeline-row {
    grid-template-columns: 1fr;
  }
}
</style>

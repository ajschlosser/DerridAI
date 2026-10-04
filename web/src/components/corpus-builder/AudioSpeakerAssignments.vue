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
import { reactive, useId, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiField from "../ui/UiField.vue";
import UiInput from "../ui/UiInput.vue";

defineOptions({ name: "AudioSpeakerAssignments" });

const props = withDefaults(
  defineProps<{
    speakers: string[];
    assignments?: Record<string, string>;
    disabled?: boolean;
  }>(),
  {
    assignments: () => ({}),
    disabled: false,
  },
);

const emit = defineEmits<{
  save: [assignments: Record<string, string>];
}>();

const i18n = useI18nStore();
const componentId = useId();
const headingId = `${componentId}-title`;
const draft = reactive<Record<string, string>>({});

function speakerControlId(speaker: string) {
  return `${componentId}-speaker-${speaker.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function synchronizeDraft() {
  const active = new Set(props.speakers);
  for (const key of Object.keys(draft)) {
    if (!active.has(key)) delete draft[key];
  }
  for (const speaker of props.speakers) {
    draft[speaker] = props.assignments[speaker] || "";
  }
}

watch(
  () => [props.speakers, props.assignments] as const,
  synchronizeDraft,
  { deep: true, immediate: true },
);

function saveSpeaker(speaker: string) {
  draft[speaker] = String(draft[speaker] || "").trim();
  emit(
    "save",
    Object.fromEntries(props.speakers.map((voice) => [voice, String(draft[voice] || "").trim()])),
  );
}
</script>

<template>
  <section class="speaker-assignments" :aria-labelledby="headingId">
    <header>
      <div>
        <h3 :id="headingId">
          {{ i18n.t("pdf_corpus.voice_assignments_title") }}
        </h3>
        <p>{{ i18n.t("pdf_corpus.voice_assignments_help") }}</p>
      </div>
    </header>
    <div class="speaker-grid">
      <UiField
        v-for="speaker in speakers"
        :key="speaker"
        :label="speaker"
        :control-id="speakerControlId(speaker)"
      >
        <template #default="{ describedby, invalid, controlId }">
          <UiInput
            :id="controlId"
            v-model="draft[speaker]"
            :aria-describedby="describedby"
            :invalid="invalid"
            :disabled="disabled"
            :placeholder="i18n.t('pdf_corpus.voice_assignment_placeholder')"
            autocomplete="off"
            @change="saveSpeaker(speaker)"
          />
        </template>
      </UiField>
    </div>
  </section>
</template>

<style scoped>
.speaker-assignments {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0 var(--space-5);
  border-top: 1px solid var(--border-subtle);
}

.speaker-assignments header {
  display: grid;
  gap: var(--space-2);
}

.speaker-assignments h3,
.speaker-assignments p {
  margin: 0;
}

.speaker-assignments h3 {
  font-size: 0.9375rem;
}

.speaker-assignments p {
  max-width: 72ch;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.5;
}

.speaker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: var(--space-4);
}
</style>

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
/**
 * The Record's own text with its annotation layers. Annotations are derived
 * navigation aids; clicking a linked mention walks the map, it does not
 * assert anything about the passage.
 */
import { computed, ref } from "vue";
import type { RecordSemanticMap } from "../../api/corpus";
import { segmentText } from "../../features/corpus-builder/domain/semanticMap";
import { useI18nStore } from "../../stores/i18n";

const LAYERS = ["entity", "quotation", "ner", "pos"] as const;
const props = defineProps<{
  text: string;
  mentions: RecordSemanticMap["mentions"];
  idPrefix: string;
}>();
const emit = defineEmits<{ walk: [nodeId: string, surface: string] }>();
const i18n = useI18nStore();

const shownLayers = ref<Set<string>>(new Set(LAYERS));
const textSegments = computed(() => segmentText(props.text, props.mentions, shownLayers.value));
function toggleLayer(layer: string, on: boolean) {
  const next = new Set(shownLayers.value);
  if (on) next.add(layer);
  else next.delete(layer);
  shownLayers.value = next;
}
</script>

<template>
  <section class="annotated-text" :aria-labelledby="`${idPrefix}-semantic-annotated-title`">
    <div class="annotated-text-head">
      <h4 :id="`${idPrefix}-semantic-annotated-title`">
        {{ i18n.t("pdf_corpus.semantic_map_annotated_text") }}
      </h4>
      <fieldset class="layer-toggles">
        <legend>{{ i18n.t("pdf_corpus.semantic_map_show_layers") }}</legend>
        <label v-for="layer in LAYERS" :key="layer" :data-layer="layer">
          <input
            type="checkbox"
            :checked="shownLayers.has(layer)"
            @change="toggleLayer(layer, ($event.target as HTMLInputElement).checked)"
          />
          {{ i18n.t(`pdf_corpus.semantic_map_layer_${layer}`) }}
        </label>
      </fieldset>
    </div>
    <p class="annotated-text-body">
      <template v-for="segment in textSegments" :key="segment.start">
        <button
          v-if="segment.mention?.node_id"
          type="button"
          class="mention"
          :data-layer="segment.mention.layer"
          :title="
            segment.mention.speaker
              ? i18n.tf('pdf_corpus.semantic_map_quotation_speaker', {
                  speaker: segment.mention.speaker,
                })
              : segment.mention.tag
          "
          :aria-label="
            i18n.tf('pdf_corpus.semantic_map_walk_to', {
              label: `${segment.text} (${segment.mention.tag || segment.mention.layer})`,
            })
          "
          @click="emit('walk', segment.mention.node_id || '', segment.text)"
        >
          {{ segment.text
          }}<small class="mention-tag" aria-hidden="true">{{
            segment.mention.tag || segment.mention.layer
          }}</small>
        </button>
        <mark
          v-else-if="segment.mention"
          class="mention"
          :data-layer="segment.mention.layer"
          :title="segment.mention.tag"
          >{{ segment.text
          }}<small class="mention-tag">{{
            segment.mention.tag || segment.mention.layer
          }}</small></mark
        >
        <template v-else>{{ segment.text }}</template>
      </template>
    </p>
  </section>
</template>

<style scoped>
.annotated-text {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
}
.annotated-text-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  align-items: center;
}
.layer-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  border: 0;
  font-size: var(--fs-xs);
}
.layer-toggles legend {
  float: left;
  margin-inline-end: var(--space-1);
  padding: 0;
  font-weight: var(--fw-semibold);
}
.annotated-text-body {
  margin: 0;
  max-height: 280px;
  overflow: auto;
  line-height: 2.2;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.mention {
  padding: 0 2px;
  border: 0;
  border-bottom: 2px solid var(--tone-info-border);
  border-radius: 2px;
  background: var(--tone-info-bg);
  color: var(--text);
  font: inherit;
  cursor: default;
}
button.mention {
  cursor: pointer;
}
.mention-tag {
  display: inline-block;
  margin-inline-start: 4px;
  padding: 0 6px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill);
  background: var(--surface-card);
  color: var(--text-2);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  line-height: 1.5;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  vertical-align: 0.15em;
  white-space: nowrap;
  user-select: none;
}
.mention[data-layer="quotation"] .mention-tag {
  border-color: var(--tone-warn-border);
}
.mention[data-layer="entity"] .mention-tag {
  border-color: var(--tone-ok-border);
}
.mention[data-layer="quotation"] {
  background: var(--tone-warn-bg);
  border-bottom-color: var(--tone-warn-border);
}
.mention[data-layer="pos"] {
  background: transparent;
  border-bottom: 2px dotted var(--border-strong);
}
.mention[data-layer="entity"] {
  background: var(--tone-ok-bg);
  border-bottom-color: var(--tone-ok-border);
}
.annotated-text h4 {
  margin: 0;
}
button.mention:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
.include-terms {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.layer-toggles label,
.include-terms {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  margin: 0;
  font-weight: var(--fw-regular);
}
.layer-toggles input,
.include-terms input {
  margin: 0;
}
</style>

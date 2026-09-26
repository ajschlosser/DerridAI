<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useId } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { RetrievalProfile } from "../api/metadataSchemas";
import UiTooltip from "./ui/UiTooltip.vue";

/** A field this policy may name as an analogy condition. */
export interface RetrievalMatchOption {
  fieldId: string;
  label: string;
}

// Edits one field's reviewed-precedent retrieval policy. Nothing here changes reviewed
// records; it only shapes which precedents future metadata enrichment may see.
const profile = defineModel<RetrievalProfile>({ required: true });
defineProps<{ matchOptions: RetrievalMatchOption[] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(`schemas.${key}`, fallback);
const matchLegendId = useId();

const help = {
  memory:
    "Controls evidence-bound human-reviewed precedents used as few-shot guidance for this metadata field. These settings never change the reviewed source record itself.",
  enabled:
    "When enabled, DerridAI may retrieve human-reviewed evidence-bound examples for this field during metadata enrichment.",
  corrections:
    "Include reviewed cases where a model value was rejected and replaced. The rejected value remains negative evidence; it is never taught as a correct answer.",
  absence:
    "Include reviewer-confirmed no-value examples only when that absence has explicit reviewed source evidence.",
  limit:
    "Maximum number of reviewed precedents for this field that may enter the bounded prompt packet. Set 0 to disable retrieval for this field without deleting its reviewed history.",
  similarity:
    "Discard semantic matches below this similarity threshold. 0 accepts any semantic similarity; 1 requires the strongest possible match.",
  maxCorrections:
    "Corrections have their own quota so they never crowd out ordinary precedents. Set 0 to use none.",
  match:
    "Optional. Prefer precedents whose reviewed value for each chosen field equals this record's reviewed value, and leave out ones that differ. A field that is unreviewed on either side is not compared.",
} as const;

function update(patch: Partial<RetrievalProfile>) {
  profile.value = { ...profile.value, ...patch };
}

function toggleMatch(fieldId: string, checked: boolean) {
  const current = new Set(profile.value.match_field_ids || []);
  if (checked) current.add(fieldId);
  else current.delete(fieldId);
  update({ match_field_ids: [...current] });
}
</script>

<template>
  <fieldset class="schema-memory">
    <legend>
      {{ t("memory", "Memory & retrieval") }}
      <UiTooltip :text="t('memory_help', help.memory)" />
    </legend>
    <label class="check">
      <input
        type="checkbox"
        :checked="profile.enabled"
        @change="update({ enabled: ($event.target as HTMLInputElement).checked })"
      />
      <span>
        {{ t("memory_enabled", "Use reviewed precedents") }}
        <UiTooltip :text="t('memory_enabled_help', help.enabled)" />
      </span>
    </label>
    <label class="check">
      <input
        type="checkbox"
        :checked="profile.include_corrections"
        @change="update({ include_corrections: ($event.target as HTMLInputElement).checked })"
      />
      <span>
        {{ t("memory_corrections", "Include corrections") }}
        <UiTooltip :text="t('memory_corrections_help', help.corrections)" />
      </span>
    </label>
    <label class="check">
      <input
        type="checkbox"
        :checked="profile.include_confirmed_absence"
        @change="update({ include_confirmed_absence: ($event.target as HTMLInputElement).checked })"
      />
      <span>
        {{ t("memory_absence", "Include confirmed absence") }}
        <UiTooltip :text="t('memory_absence_help', help.absence)" />
      </span>
    </label>
    <div class="schema-memory-numbers">
      <label>
        <span>
          {{ t("memory_limit", "Maximum precedents") }}
          <UiTooltip :text="t('memory_limit_help', help.limit)" />
        </span>
        <input
          class="control"
          type="number"
          min="0"
          max="50"
          :value="profile.max_items"
          @change="update({ max_items: Number(($event.target as HTMLInputElement).value) || 0 })"
        />
      </label>
      <label>
        <span>
          {{ t("memory_max_corrections", "Maximum corrections") }}
          <UiTooltip :text="t('memory_max_corrections_help', help.maxCorrections)" />
        </span>
        <input
          class="control"
          type="number"
          min="0"
          max="20"
          :disabled="!profile.include_corrections"
          :value="profile.max_corrections ?? 2"
          @change="
            update({ max_corrections: Number(($event.target as HTMLInputElement).value) || 0 })
          "
        />
      </label>
      <label>
        <span>
          {{ t("memory_similarity", "Minimum similarity") }}
          <UiTooltip :text="t('memory_similarity_help', help.similarity)" />
        </span>
        <input
          class="control"
          type="number"
          min="0"
          max="1"
          step="0.05"
          :value="profile.min_similarity"
          @change="
            update({ min_similarity: Number(($event.target as HTMLInputElement).value) || 0 })
          "
        />
      </label>
    </div>
    <div class="schema-memory-match" role="group" :aria-labelledby="matchLegendId">
      <span :id="matchLegendId" class="schema-memory-match-title">
        {{ t("memory_match_fields", "Prefer precedents that agree on") }}
        <UiTooltip :text="t('memory_match_fields_help', help.match)" />
      </span>
      <p v-if="!matchOptions.length" class="hint">
        {{ t("memory_match_none", "No other fields are available to compare.") }}
      </p>
      <label v-for="option in matchOptions" :key="option.fieldId" class="check">
        <input
          type="checkbox"
          :checked="(profile.match_field_ids || []).includes(option.fieldId)"
          @change="toggleMatch(option.fieldId, ($event.target as HTMLInputElement).checked)"
        />
        <span>{{ option.label }}</span>
      </label>
    </div>
    <small class="hint">{{
      t(
        "memory_help",
        "These controls affect only retrieval of reviewed precedents during future metadata enrichment; the canonical reviewed record and evidence remain unchanged.",
      )
    }}</small>
  </fieldset>
</template>

<style scoped>
.schema-memory {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 14px;
  align-content: start;
  min-inline-size: min(100%, 18rem);
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
}
.schema-memory legend {
  padding: 0 4px;
  font-size: 0.8125rem;
  font-weight: 750;
}
.schema-memory-numbers,
.schema-memory-match,
.schema-memory > .hint {
  grid-column: 1 / -1;
}
.schema-memory-numbers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 8px;
}
.schema-memory-numbers label {
  display: grid;
  gap: 4px;
  font-size: 0.75rem;
  font-weight: 650;
}
.schema-memory-match {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  align-items: center;
}
.schema-memory-match-title {
  flex-basis: 100%;
  font-size: 0.75rem;
  font-weight: 650;
}
.check {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 0.8125rem;
  font-weight: 500;
}
.hint {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 500;
  margin: 0;
}
@media (max-width: 820px) {
  .schema-memory,
  .schema-memory-numbers {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

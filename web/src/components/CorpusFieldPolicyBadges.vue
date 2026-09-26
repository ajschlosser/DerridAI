<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { SchemaField } from "../api/metadataSchemas";
import { useI18nStore } from "../stores/i18n";
import UiTooltip from "./ui/UiTooltip.vue";

const props = defineProps<{
  field: string;
  schemaField?: SchemaField | null;
  coreRequired?: boolean;
}>();
const i18n = useI18nStore();

const humanDecision = computed(() => Boolean(props.coreRequired || props.schemaField?.review));
const evidenceRequired = computed(() => Boolean(props.coreRequired || props.schemaField?.evidence));
const memory = computed(() => props.schemaField?.retrieval_profile || null);
const memoryEnabled = computed(() =>
  Boolean(memory.value?.enabled && Number(memory.value.max_items || 0) > 0),
);
const memoryHelp = computed(() => {
  const profile = memory.value;
  if (!profile) return "";
  const parts = [
    i18n.tf("pdf_corpus.field_memory_max", "Up to {count} reviewed precedents", {
      count: Number(profile.max_items || 0),
    }),
    i18n.tf("pdf_corpus.field_memory_similarity", "minimum similarity {value}", {
      value: Number(profile.min_similarity || 0).toFixed(2),
    }),
  ];
  if (profile.include_corrections)
    parts.push(i18n.t("pdf_corpus.field_memory_corrections", "includes corrections"));
  if (profile.include_confirmed_absence)
    parts.push(i18n.t("pdf_corpus.field_memory_absence", "includes confirmed absence"));
  return parts.join(" · ");
});
// Only what changes how the reviewer decides is named; "optional" and configuration details stay in the schema editor.
const notes = computed(() =>
  [
    props.coreRequired ? i18n.t("pdf_corpus.field_required", "Required") : "",
    humanDecision.value ? i18n.t("pdf_corpus.field_human_decision", "Human decision") : "",
    evidenceRequired.value ? i18n.t("pdf_corpus.field_evidence_required", "Evidence required") : "",
  ].filter(Boolean),
);
</script>

<template>
  <p
    v-if="notes.length || memoryEnabled"
    class="field-policy"
    :aria-label="i18n.t('pdf_corpus.field_configuration', 'Field configuration')"
  >
    <span v-for="note in notes" :key="note">{{ note }}</span>
    <span v-if="memoryEnabled" class="field-policy-memory"
      >{{ i18n.t("pdf_corpus.field_memory_on", "Memory on")
      }}<UiTooltip
        v-if="memoryHelp"
        :text="memoryHelp"
        :label="i18n.t('pdf_corpus.field_memory_details', 'Memory and retrieval details')"
        placement="bottom"
    /></span>
  </p>
</template>

<style scoped>
.field-policy {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0 0.5rem;
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.field-policy > span + span::before {
  content: "·";
  margin-inline-end: 0.5rem;
}
.field-policy-memory {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
}
</style>

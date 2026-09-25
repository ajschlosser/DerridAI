<script setup lang="ts">
import { computed } from "vue";
import type { SchemaField } from "../api/metadataSchemas";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";
import UiTooltip from "./ui/UiTooltip.vue";

const props = defineProps<{
  field: string;
  schemaField?: SchemaField | null;
  coreRequired?: boolean;
}>();
const i18n = useI18nStore();

const humanDecision = computed(() => Boolean(props.coreRequired || props.schemaField?.review));
const evidenceRequired = computed(() =>
  Boolean(props.coreRequired || props.schemaField?.evidence),
);
const confidenceAssessed = computed(() =>
  Boolean(props.coreRequired || props.schemaField?.assess),
);
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
</script>

<template>
  <div
    class="field-policy"
    :aria-label="i18n.t('pdf_corpus.field_configuration', 'Field configuration')"
  >
    <UiStatusBadge
      :label="
        coreRequired
          ? i18n.t('pdf_corpus.field_required', 'Required')
          : i18n.t('pdf_corpus.field_optional', 'Optional')
      "
      :tone="coreRequired ? 'info' : 'neutral'"
      :show-dot="false"
    />
    <UiStatusBadge
      v-if="humanDecision"
      :label="i18n.t('pdf_corpus.field_human_decision', 'Human decision')"
      tone="warning"
      :show-dot="false"
    />
    <UiStatusBadge
      v-if="evidenceRequired"
      :label="i18n.t('pdf_corpus.field_evidence_required', 'Evidence required')"
      tone="info"
      :show-dot="false"
    />
    <UiStatusBadge
      v-if="confidenceAssessed"
      :label="i18n.t('pdf_corpus.field_confidence_assessed', 'Confidence assessed')"
      tone="neutral"
      :show-dot="false"
    />
    <span v-if="memoryEnabled" class="field-policy-memory">
      <UiStatusBadge
        :label="i18n.t('pdf_corpus.field_memory_on', 'Memory on')"
        tone="success"
        :show-dot="false"
      />
      <UiTooltip
        v-if="memoryHelp"
        :text="memoryHelp"
        :label="i18n.t('pdf_corpus.field_memory_details', 'Memory and retrieval details')"
        placement="bottom"
      />
    </span>
  </div>
</template>

<style scoped>
.field-policy {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  margin: 0 0 0.375rem;
}
.field-policy-memory {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
}
</style>

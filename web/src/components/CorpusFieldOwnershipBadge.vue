<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";
const props = defineProps<{
  status?: string;
  method?: string;
  verification?: string;
  source?: string;
  audit?: boolean;
}>();
const i18n = useI18nStore();
const sourceKind = computed(() => {
  const status = String(props.status || ""),
    method = String(props.method || ""),
    valueSource = String(props.source || "");
  if (status === "human_override") return "override";
  if (status === "human_confirmed" || status === "confirmed_absent") return "human";
  if (status === "inherited") return "inherited";
  if (
    method.includes("llm") ||
    method === "hybrid" ||
    status === "model_inferred" ||
    valueSource === "llm"
  )
    return "llm";
  if (status === "deterministic") return "deterministic";
  return "unknown";
});
const sourceLabel = computed(() =>
  i18n.t(
    `pdf_corpus.ownership.${sourceKind.value}`,
    (
      {
        override: "Override",
        human: "Human confirmed",
        inherited: "Inherited",
        deterministic: "Source derived",
        llm: "LLM source",
        unknown: "Unclassified",
      } as Record<string, string>
    )[sourceKind.value],
  ),
);
const sourceHelp = computed(() =>
  i18n.t(
    `pdf_corpus.ownership_help.${sourceKind.value}`,
    (
      {
        override: "This record deliberately overrides document-level metadata.",
        human: "A reviewer confirmed this record-level value.",
        inherited: "Inherited from the document manifest; it may be overridden for this record.",
        deterministic: "Derived from source structure or deterministic rules.",
        llm: "The current value or proposal originated with a language model. Verification is shown separately.",
        unknown: "No source provenance has been recorded.",
      } as Record<string, string>
    )[sourceKind.value],
  ),
);
const sourceTone = computed(() =>
  sourceKind.value === "human" || sourceKind.value === "override"
    ? "success"
    : sourceKind.value === "llm"
      ? "info"
      : "neutral",
);
const verificationKind = computed(() => {
  const explicit = String(props.verification || "");
  if (explicit) return explicit;
  const status = String(props.status || "");
  if (status === "unresolved" || status === "invalid") return "pending_review";
  if (status === "model_inferred") return "auto_resolved";
  if (
    status === "human_confirmed" ||
    status === "human_override" ||
    status === "confirmed_absent"
  )
    return "human_confirmed";
  return "";
});
const verificationLabel = computed(() =>
  verificationKind.value === "pending_review"
    ? i18n.t("pdf_corpus.verification.pending", "Needs review")
    : verificationKind.value === "auto_resolved"
      ? i18n.t("pdf_corpus.verification.auto", "Auto-resolved")
      : verificationKind.value === "human_confirmed"
        ? i18n.t("pdf_corpus.verification.human", "Human confirmed")
        : "",
);
</script>
<template>
  <span class="ownership-badges"
    ><UiStatusBadge :label="sourceLabel" :help="sourceHelp" :tone="sourceTone" /><UiStatusBadge
      v-if="sourceKind === 'llm' && verificationLabel"
      :label="verificationLabel"
      :help="
        verificationKind === 'auto_resolved'
          ? i18n.t(
              'pdf_corpus.verification_help.auto',
              'Calibrated autofill approved this value without requiring a field-level human decision.',
            )
          : i18n.t(
              'pdf_corpus.verification_help.pending',
              'The model value is visible but still requires a human decision.',
            )
      "
      :tone="verificationKind === 'auto_resolved' ? 'success' : 'warning'" /><UiStatusBadge
      v-if="audit && sourceKind === 'llm'"
      :label="i18n.t('pdf_corpus.ownership.spot_check', 'Spot check')"
      :help="
        i18n.t(
          'pdf_corpus.ownership_help.spot_check',
          'This value was filled in automatically and was picked at random for a quick check. Confirm or correct it.',
        )
      "
      tone="warning"
  /></span>
</template>
<style scoped>
.ownership-badges {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  align-items: center;
}
</style>

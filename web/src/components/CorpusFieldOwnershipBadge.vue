<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

const props = defineProps<{
  status?: string;
  method?: string;
  derivationMethod?: string;
  verification?: string;
  source?: string;
  audit?: boolean;
}>();
const i18n = useI18nStore();

const sourceKind = computed(() => {
  const status = String(props.status || "");
  const method = String(props.method || "");
  const derivation = String(props.derivationMethod || "");
  const valueSource = String(props.source || "");

  if (status === "human_override") return "override";
  if (derivation === "model") return "llm";
  if (derivation === "inherited") return "inherited";
  if (derivation === "deterministic") return "deterministic";
  if (derivation === "human") return "human";
  if (status === "inherited") return "inherited";
  if (status === "deterministic") return "deterministic";
  if (
    method.includes("llm") ||
    method === "hybrid" ||
    status === "model_inferred" ||
    valueSource === "llm"
  )
    return "llm";
  if (status === "human_confirmed" || status === "confirmed_absent") return "human";
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
  if (status === "human_confirmed" || status === "human_override" || status === "confirmed_absent")
    return "human_confirmed";
  return "";
});

const verificationLabel = computed(() =>
  verificationKind.value === "pending_review"
    ? i18n.t("pdf_corpus.verification.pending")
    : verificationKind.value === "auto_resolved"
      ? i18n.t("pdf_corpus.verification.auto")
      : verificationKind.value === "human_confirmed"
        ? i18n.t("pdf_corpus.verification.human")
        : "",
);

const showVerification = computed(
  () =>
    Boolean(verificationLabel.value) &&
    (sourceKind.value === "llm" ||
      (verificationKind.value === "human_confirmed" &&
        sourceKind.value !== "human" &&
        sourceKind.value !== "override")),
);

const verificationHelp = computed(() =>
  verificationKind.value === "auto_resolved"
    ? i18n.t("pdf_corpus.verification_help.auto")
    : verificationKind.value === "human_confirmed"
      ? i18n.t("pdf_corpus.ownership_help.human")
      : i18n.t("pdf_corpus.verification_help.pending"),
);
</script>

<template>
  <span class="ownership-badges">
    <UiStatusBadge :label="sourceLabel" :help="sourceHelp" :tone="sourceTone" />
    <UiStatusBadge
      v-if="showVerification"
      :label="verificationLabel"
      :help="verificationHelp"
      :tone="
        verificationKind === 'human_confirmed' || verificationKind === 'auto_resolved'
          ? 'success'
          : 'warning'
      "
    />
    <UiStatusBadge
      v-if="audit && sourceKind === 'llm'"
      :label="i18n.t('pdf_corpus.ownership.spot_check')"
      :help="i18n.t('pdf_corpus.ownership_help.spot_check')"
      tone="warning"
    />
  </span>
</template>

<style scoped>
.ownership-badges {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  align-items: center;
}
</style>

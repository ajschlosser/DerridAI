<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";
const props = defineProps<{
  status?: string;
  method?: string;
  /** The assertion's derivation method; namespaced values (derridai:memory, :nlp, :computed) get their own labels. */
  derivation?: string;
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
  const derivation = String(props.derivation || "");
  if (derivation === "derridai:memory") return "memory";
  if (derivation === "derridai:nlp") return "nlp";
  if (derivation === "derridai:computed") return "computed";
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
        memory: "Metadata memory",
        nlp: "NLP-derived",
        computed: "Computed",
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
        memory:
          "Suggested by earlier reviewed precedents whose evidence matches this source span. A reviewer must confirm it.",
        nlp: "Proposed by a statistical language tagger. A reviewer must confirm it.",
        computed: "Computed from an exact pattern or arithmetic. A reviewer must confirm it.",
        unknown: "No source provenance has been recorded.",
      } as Record<string, string>
    )[sourceKind.value],
  ),
);
const sourceTone = computed(() =>
  sourceKind.value === "human" || sourceKind.value === "override"
    ? "success"
    : ["llm", "memory", "nlp"].includes(sourceKind.value)
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
</script>
<template>
  <span class="ownership-badges"
    ><UiStatusBadge :label="sourceLabel" :help="sourceHelp" :tone="sourceTone" /><UiStatusBadge
      v-if="sourceKind === 'llm' && verificationLabel"
      :label="verificationLabel"
      :help="
        verificationKind === 'auto_resolved'
          ? i18n.t('pdf_corpus.verification_help.auto')
          : i18n.t('pdf_corpus.verification_help.pending')
      "
      :tone="verificationKind === 'auto_resolved' ? 'success' : 'warning'" /><UiStatusBadge
      v-if="audit && sourceKind === 'llm'"
      :label="i18n.t('pdf_corpus.ownership.spot_check')"
      :help="i18n.t('pdf_corpus.ownership_help.spot_check')"
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

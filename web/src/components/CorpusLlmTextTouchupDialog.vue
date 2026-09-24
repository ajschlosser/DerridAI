<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ProviderProfile } from "../api/system";
import UiDialog from "./ui/UiDialog.vue";
import UiButton from "./ui/UiButton.vue";
import LlmExecutionControl from "./LlmExecutionControl.vue";
import { useI18nStore } from "../stores/i18n";
import { llmDiffSides, llmDiffSummary } from "../domain/reviewPresentation";
const props = defineProps<{
  open: boolean;
  sourceText: string;
  proposedText?: string;
  changes?: string[];
  warnings?: string[];
  model?: string;
  provider?: string;
  proposalId?: string;
  runId?: string;
  proposalCreatedAt?: string;
  proposalStatus?: string;
  error?: string;
  busy?: boolean;
  noChange?: boolean;
  profiles: ProviderProfile[];
  providerProfileId: string;
  modelOverride?: string;
  recordId?: string;
  concurrencyRisk?: boolean;
  activeRequests?: number;
  concurrencyLimit?: number;
}>();
const emit = defineEmits<{
  close: [];
  run: [instructions: string, providerProfileId: string, model: string];
  apply: [text: string];
  dismiss: [];
  "update:providerProfileId": [value: string];
  "update:modelOverride": [value: string];
}>();
const i18n = useI18nStore();
const instructions = ref("");
const draft = ref("");
const operationMessage = ref("");
const textDiff = computed(() => {
  if (!props.proposedText || props.proposedText === props.sourceText) return null;
  return llmDiffSides("text", props.sourceText, props.proposedText);
});
const diffSummary = computed(() => {
  if (!props.proposedText || props.proposedText === props.sourceText) return null;
  return llmDiffSummary(props.sourceText, props.proposedText);
});
const redundant = computed(() => {
  const text = instructions.value.toLowerCase().replace(/[^a-z0-9 ]/g, " ");
  if (text.trim().length < 8) return false;
  const patterns = [
    /ocr/,
    /do not paraphrase|don t paraphrase|preserve (the )?(wording|meaning|text)/,
    /punctuation|spacing|line wrap/,
    /page number|header|footer/,
    /correct.*err(or|ata)/,
  ];
  return patterns.some((p) => p.test(text));
});
function reset() {
  instructions.value = "";
  draft.value = "";
  operationMessage.value = "";
}
watch(
  () => [props.proposedText, props.recordId] as const,
  ([value]) => {
    draft.value = String(value || "");
    if (value)
      operationMessage.value = i18n.t("pdf_corpus.llm_touchup_ready");
  },
  { immediate: true },
);
watch(
  () => [props.open, props.recordId] as const,
  (value, old) => {
    if (value[0] && (!old?.[0] || value[1] !== old?.[1])) {
      reset();
      draft.value = String(props.proposedText || "");
    }
  },
);
watch(
  () => props.busy,
  (value) => {
    if (value)
      operationMessage.value = i18n.t("pdf_corpus.llm_touchup_contacting");
  },
);
function run() {
  if (!props.providerProfileId) return;
  draft.value = "";
  operationMessage.value = i18n.t("pdf_corpus.llm_touchup_contacting");
  emit("run", instructions.value, props.providerProfileId, String(props.modelOverride || ""));
}
</script>
<template>
  <UiDialog
    :open="open"
    size="xlarge"
    :title="i18n.t('pdf_corpus.llm_touchup_title')"
    :description="
      i18n.tf('pdf_corpus.llm_touchup_help')
    "
    :close-label="i18n.t('ui.close')"
    @close="emit('close')"
    ><LlmExecutionControl
      :model-value="providerProfileId"
      :model-override="modelOverride"
      :profiles="profiles"
      :disabled="busy"
      :task="
        i18n.t('pdf_corpus.llm_touchup_provider_help')
      "
      :concurrency-risk="concurrencyRisk"
      :active-requests="activeRequests"
      :concurrency-limit="concurrencyLimit"
      @update:model-value="(value) => emit('update:providerProfileId', value)"
      @update:model-override="(value) => emit('update:modelOverride', value)" />
    <details class="built-in-policy">
      <summary>
        {{
          i18n.t("pdf_corpus.touchup_builtin_policy")
        }}
      </summary>
      <p>
        {{
          i18n.t("pdf_corpus.touchup_builtin_policy_help")
        }}
      </p>
    </details>
    <div class="touchup-controls">
      <label
        ><span>{{ i18n.t("pdf_corpus.llm_touchup_instruction") }}</span
        ><input
          v-model="instructions"
          class="control"
          :placeholder="
            i18n.t('pdf_corpus.llm_touchup_instruction_placeholder')
          "
          aria-describedby="touchup-instruction-help" /></label
      ><UiButton
        variant="primary"
        :disabled="busy || !providerProfileId"
        :label="
          busy
            ? i18n.t('pdf_corpus.llm_touchup_running')
            : i18n.t('pdf_corpus.run_llm_touchup')
        "
        @click="run"
      />
    </div>
    <p id="touchup-instruction-help" v-if="redundant" class="redundant-warning" role="status">
      {{
        i18n.t("pdf_corpus.touchup_redundant_instruction")
      }}
    </p>
    <p v-if="error" class="operation-error" role="alert">{{ error }}</p>
    <p v-else-if="noChange" class="operation-status" aria-live="polite">
      {{
        i18n.t("pdf_corpus.llm_touchup_no_change")
      }}
    </p>
    <p v-else-if="operationMessage" class="operation-status" aria-live="polite">
      {{ operationMessage }}
    </p>
    <p v-if="model" class="model-note">
      {{ i18n.tf("pdf_corpus.llm_touchup_model", { model }) }}
    </p>
    <p v-if="provider || proposalId || runId" class="model-note proposal-context">
      {{
        i18n.tf("pdf_corpus.llm_touchup_context", {
            provider: provider || "—",
            proposal: proposalId || "—",
            run: runId || "—",
          })
      }}
      <span v-if="proposalCreatedAt">
        ·
        {{
          i18n.tf("pdf_corpus.llm_touchup_created", { at: proposalCreatedAt })
        }}</span
      >
    </p>
    <div v-if="proposedText && !noChange" class="touchup-grid">
      <section>
        <h3>{{ i18n.t("pdf_corpus.cleanup_before") }}</h3>
        <pre>{{ sourceText }}</pre>
      </section>
      <section>
        <h3>{{ i18n.t("pdf_corpus.llm_touchup_proposed") }}</h3>
        <div v-if="textDiff" class="touchup-diff" aria-live="polite">
          <div class="touchup-diff-label">
            {{ i18n.t("pdf_corpus.llm_touchup_diff_preview") }}
          </div>
          <div class="touchup-diff-columns">
            <pre class="change-diff current-diff" v-html="textDiff.left"></pre>
            <pre class="change-diff proposed-diff" v-html="textDiff.right"></pre>
          </div>
        </div>
        <textarea v-model="draft" :aria-label="i18n.t('pdf_corpus.llm_touchup_proposed')"></textarea>
      </section>
    </div>
    <p v-if="diffSummary" class="touchup-change-summary" role="status">
      {{
        i18n.tf("pdf_corpus.llm_touchup_change_summary", {
            removed: diffSummary.removed,
            added: diffSummary.added,
            before: diffSummary.before,
            after: diffSummary.after,
          })
      }}
    </p>
    <div v-if="!noChange && (changes?.length || warnings?.length)" class="touchup-notes">
      <section v-if="changes?.length">
        <h3>{{ i18n.t("pdf_corpus.llm_touchup_changes") }}</h3>
        <ul>
          <li v-for="item in changes" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section v-if="warnings?.length">
        <h3>{{ i18n.t("pdf_corpus.llm_touchup_warnings") }}</h3>
        <ul>
          <li v-for="item in warnings" :key="item">{{ item }}</li>
        </ul>
      </section>
    </div>
    <template #footer
      ><span class="footer-note">{{
        i18n.t("pdf_corpus.llm_touchup_source_preserved")
      }}</span>
      <div>
        <UiButton :label="i18n.t('ui.cancel')" @click="emit('close')" /><UiButton
          v-if="proposalStatus === 'pending_review' && proposalId"
          :label="i18n.t('pdf_corpus.dismiss_llm_touchup')"
          @click="emit('dismiss')"
        /><UiButton
          v-if="proposedText && !noChange"
          variant="primary"
          :disabled="!draft.trim() || busy"
          :label="i18n.t('pdf_corpus.apply_llm_touchup')"
          @click="emit('apply', draft)"
        /></div></template
  ></UiDialog>
</template>
<style scoped>
.touchup-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
  margin-top: 14px;
}
.touchup-controls label {
  display: grid;
  gap: 5px;
  font-size: 0.875rem;
  font-weight: 700;
}
.control {
  min-height: 42px;
}
.model-note,
.footer-note,
.operation-status {
  font-size: 0.8125rem;
  color: var(--muted);
}
.operation-error {
  margin: 8px 0 0;
  padding: 9px 10px;
  border: 1px solid var(--tone-danger-border);
  border-radius: 8px;
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.built-in-policy {
  margin-top: 12px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
}
.built-in-policy summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 750;
}
.built-in-policy p {
  margin: 7px 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
.redundant-warning {
  margin: 8px 0 0;
  padding: 9px 10px;
  border: 1px solid var(--warning, #a16207);
  border-radius: 8px;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.touchup-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}
.touchup-grid h3,
.touchup-notes h3 {
  font-size: 0.9375rem;
  margin: 0 0 6px;
}
.touchup-grid pre,
.touchup-grid textarea {
  box-sizing: border-box;
  width: 100%;
  height: 360px;
  margin: 0;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
  white-space: pre-wrap;
  font:
    15px/1.6 Georgia,
    serif;
}
.touchup-grid textarea {
  resize: vertical;
  background: var(--card);
  color: var(--text);
}
.touchup-diff {
  margin-bottom: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
}
.touchup-diff-label {
  padding: 7px 10px;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.touchup-diff-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.touchup-diff-columns pre {
  height: 180px;
  border: 0;
  border-radius: 0;
  background: var(--card);
  font-size: 13px;
}
.touchup-diff-columns pre + pre {
  border-left: 1px solid var(--line);
}
.touchup-change-summary {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.touchup-notes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}
.touchup-notes section {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
  font-size: 0.875rem;
  line-height: 1.45;
}
.touchup-notes ul {
  margin: 0;
  padding-inline-start: 20px;
}
.touchup-controls :focus-visible,
.touchup-grid textarea:focus-visible,
summary:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 760px) {
  .touchup-controls,
  .touchup-grid,
  .touchup-notes {
    grid-template-columns: 1fr;
  }
  .touchup-grid pre,
  .touchup-grid textarea {
    height: 260px;
  }
}
</style>

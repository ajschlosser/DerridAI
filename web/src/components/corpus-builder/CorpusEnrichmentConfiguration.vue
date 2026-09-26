<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref, toRefs } from "vue";
import type { ProviderProfile } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import CorpusTextNoiseSettings from "../CorpusTextNoiseSettings.vue";
import ProviderProfileSelect from "../ProviderProfileSelect.vue";

type EnrichmentMode = "fast" | "deep";
type ManualProvider = "ollama" | "openai";

const props = defineProps<{
  providerProfiles: ProviderProfile[];
  defaultProfileId: string;
  selectedProviderLabel: string;
  selectedProfileModel: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ manageProviders: [] }>();

const selectedProviderId = defineModel<string>("selectedProviderId", { required: true });
const selectedReviewProviderId = defineModel<string>("selectedReviewProviderId", {
  required: true,
});
const enrichmentMode = defineModel<EnrichmentMode>("enrichmentMode", { required: true });
const semanticIndexing = defineModel<boolean>("semanticIndexing", { required: true });
const autoCleanText = defineModel<boolean>("autoCleanText", { required: true });
const llmTouchupDuringEnrichment = defineModel<boolean>("llmTouchupDuringEnrichment", {
  required: true,
});
const noiseUnusableThreshold = defineModel<number>("noiseUnusableThreshold", { required: true });
const llmAssessTextNoise = defineModel<boolean>("llmAssessTextNoise", { required: true });
const manualProvider = defineModel<ManualProvider>("manualProvider", { required: true });
const manualModel = defineModel<string>("manualModel", { required: true });
const manualBaseUrl = defineModel<string>("manualBaseUrl", { required: true });
const manualApiKey = defineModel<string>("manualApiKey", { required: true });

const i18n = useI18nStore();
const { selectedProviderLabel, selectedProfileModel } = toRefs(props);
const advancedOpen = ref(false);
</script>

<template>
  <details
    id="corpus-config-panel-enrichment"
    class="setup-section setup-disclosure"
    role="tabpanel"
    aria-labelledby="corpus-config-tab-enrichment"
    open
  >
    <summary>
      <span
        ><b>{{ i18n.t("pdf_corpus.llm_enrichment_title") }}</b
        ><small
          >{{ selectedProviderLabel }}<template v-if="selectedProfileModel">
            · {{ selectedProfileModel }}</template
          >
          ·
          {{
            enrichmentMode === "deep"
              ? i18n.t("pdf_corpus.enrichment_deep")
              : i18n.t("pdf_corpus.enrichment_fast")
          }}</small
        ></span
      >
    </summary>
    <div class="setup-disclosure-body">
      <div class="provider-area">
        <ProviderProfileSelect
          v-model="selectedProviderId"
          :profiles="props.providerProfiles"
          :default-profile-id="props.defaultProfileId"
          :label="i18n.t('pdf_corpus.provider_profile')"
          :help="i18n.t('pdf_corpus.provider_profile_help')"
          :empty-title="i18n.t('pdf_corpus.no_provider_profiles')"
          :empty-help="i18n.t('pdf_corpus.no_provider_profiles_help')"
          :manage-label="i18n.t('pdf_corpus.manage_providers')"
          :model-not-set-label="i18n.t('pdf_corpus.model_not_set')"
          :default-label="i18n.t('ui.default')"
          :concurrent-label="i18n.t('pdf_corpus.concurrent_requests')"
          :context-label="i18n.t('providers.context_tokens')"
          @manage="emit('manageProviders')"
        />
        <label
          v-if="selectedProviderId && props.providerProfiles.length > 1"
          class="escalation-field"
          for="pdf-corpus-review-provider"
          ><span
            ><b>{{ i18n.t("pdf_corpus.escalation_provider") }}</b
            ><small>{{ i18n.t("pdf_corpus.escalation_provider_help") }}</small></span
          ><select
            id="pdf-corpus-review-provider"
            v-model="selectedReviewProviderId"
            class="control"
          >
            <option value="">
              {{ i18n.t("pdf_corpus.no_escalation_provider") }}
            </option>
            <option
              v-for="profile in props.providerProfiles"
              :key="profile.id"
              :value="profile.id"
              :disabled="profile.id === selectedProviderId"
            >
              {{ profile.name || profile.id }} ·
              {{ profile.model || i18n.t("pdf_corpus.model_not_set") }}
            </option>
          </select></label
        >
      </div>
      <section class="enrichment-strategy" aria-labelledby="pdf-corpus-enrichment-mode-title">
        <div class="setup-card-heading">
          <b id="pdf-corpus-enrichment-mode-title">{{ i18n.t("pdf_corpus.enrichment_strategy") }}</b
          ><small>{{ i18n.t("pdf_corpus.enrichment_strategy_help") }}</small>
        </div>
        <div
          class="mode-options"
          role="radiogroup"
          :aria-label="i18n.t('pdf_corpus.enrichment_strategy')"
        >
          <label
            ><input v-model="enrichmentMode" type="radio" value="fast" /><span
              ><b>{{ i18n.t("pdf_corpus.enrichment_fast") }}</b
              ><small>{{ i18n.t("pdf_corpus.enrichment_fast_help") }}</small></span
            ></label
          ><label
            ><input v-model="enrichmentMode" type="radio" value="deep" /><span
              ><b>{{ i18n.t("pdf_corpus.enrichment_deep") }}</b
              ><small>{{ i18n.t("pdf_corpus.enrichment_deep_help") }}</small></span
            ></label
          >
        </div>
        <div v-if="enrichmentMode === 'deep'" class="included-feature">
          <b>{{ i18n.t("pdf_corpus.semantic_indexing") }}</b
          ><span>{{ i18n.t("pdf_corpus.semantic_indexing_included") }}</span>
        </div>
        <label v-else class="semantic-index-toggle"
          ><input v-model="semanticIndexing" type="checkbox" /><span
            ><b>{{ i18n.t("pdf_corpus.semantic_indexing") }}</b
            ><small>{{ i18n.t("pdf_corpus.semantic_indexing_help") }}</small></span
          ></label
        >
        <label class="semantic-index-toggle"
          ><input v-model="autoCleanText" type="checkbox" /><span
            ><b>{{ i18n.t("pdf_corpus.auto_clean_all_records") }}</b
            ><small>{{ i18n.t("pdf_corpus.auto_clean_all_records_help") }}</small></span
          ></label
        ><label class="semantic-index-toggle"
          ><input v-model="llmTouchupDuringEnrichment" type="checkbox" /><span
            ><b>{{ i18n.t("pdf_corpus.llm_touchup_during_enrichment") }}</b
            ><small>{{ i18n.t("pdf_corpus.llm_touchup_during_enrichment_help") }}</small></span
          ></label
        >
        <CorpusTextNoiseSettings
          :threshold="noiseUnusableThreshold"
          :llm-assist="llmAssessTextNoise"
          :disabled="props.disabled"
          @update:threshold="noiseUnusableThreshold = $event"
          @update:llm-assist="llmAssessTextNoise = $event"
        />
      </section>
      <details
        v-if="!selectedProviderId"
        :open="advancedOpen"
        class="advanced-config"
        @toggle="advancedOpen = ($event.currentTarget as HTMLDetailsElement).open"
      >
        <summary>
          {{ i18n.t("pdf_corpus.manual_provider") }}
        </summary>
        <p class="help">
          {{ i18n.t("pdf_corpus.manual_provider_help") }}
        </p>
        <div class="advanced-grid">
          <label for="pdf-corpus-provider">{{ i18n.t("pdf_corpus.provider") }}</label
          ><select id="pdf-corpus-provider" v-model="manualProvider" class="control">
            <option value="ollama">Ollama</option>
            <option value="openai">
              {{ i18n.t("pdf_corpus.openai_compatible") }}
            </option></select
          ><label for="pdf-corpus-model">{{ i18n.t("pdf_corpus.model") }}</label
          ><input
            id="pdf-corpus-model"
            v-model="manualModel"
            class="control"
            :placeholder="i18n.t('pdf_corpus.provider_default')"
          /><label for="pdf-corpus-url">{{ i18n.t("pdf_corpus.base_url") }}</label
          ><input
            id="pdf-corpus-url"
            v-model="manualBaseUrl"
            class="control"
            :placeholder="i18n.t('pdf_corpus.provider_default')"
          /><label for="pdf-corpus-key">{{ i18n.t("pdf_corpus.api_key") }}</label
          ><input
            id="pdf-corpus-key"
            v-model="manualApiKey"
            class="control"
            type="password"
            autocomplete="off"
            :placeholder="i18n.t('pdf_corpus.not_persisted')"
          />
        </div>
      </details>
    </div>
  </details>
</template>

<style scoped>
.setup-disclosure {
  overflow: visible;
  border-top: 1px solid var(--border-subtle);
}
.setup-disclosure > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 54px;
  padding: var(--space-3) 0;
}
.setup-disclosure > summary::-webkit-details-marker {
  display: none;
}
.setup-disclosure > summary > span:last-child {
  display: grid;
  gap: 2px;
}
.setup-disclosure > summary b {
  font-size: 0.9375rem;
}
.setup-disclosure > summary small {
  color: var(--muted);
  font-size: 0.8125rem !important;
  font-weight: 500;
}
.setup-disclosure[open] > summary {
  border-bottom: 1px solid var(--border-subtle);
  background: transparent;
}
.setup-disclosure-body {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0 var(--space-5);
}
.provider-area {
  display: grid;
  gap: 8px;
  padding: 0;
  border: 0;
}
.setup-card-heading {
  display: grid;
  gap: 3px;
}
.setup-card-heading b {
  font-size: 0.8125rem;
}
.setup-card-heading small {
  font-size: 0.8125rem !important;
  line-height: 1.45;
}
.escalation-field {
  display: grid;
  grid-template-columns: minmax(150px, 0.7fr) minmax(220px, 1fr);
  gap: 12px;
  align-items: center;
  padding: 10px 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.escalation-field > span {
  display: grid;
  gap: 2px;
}
.escalation-field b {
  font-size: 0.8125rem;
}
.escalation-field small {
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--muted);
}
.advanced-config {
  grid-column: 1/-1;
}
.advanced-config summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}
.advanced-grid {
  display: grid;
  grid-template-columns: max-content 1fr max-content 1fr;
  gap: 8px 10px;
  margin-top: 8px;
  align-items: center;
}
.enrichment-strategy {
  display: grid;
  gap: 12px;
  padding-top: 2px;
}
.mode-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.mode-options > label,
.semantic-index-toggle {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  cursor: pointer;
}
.mode-options input,
.semantic-index-toggle input {
  inline-size: 18px;
  block-size: 18px;
  flex: 0 0 auto;
  margin-top: 2px;
  accent-color: var(--accent);
}
.mode-options span,
.semantic-index-toggle span {
  display: grid;
  gap: 4px;
}
.mode-options b,
.semantic-index-toggle b {
  font-size: 0.875rem;
}
.mode-options small,
.semantic-index-toggle small {
  font-size: 0.8125rem !important;
  color: var(--muted);
}
.mode-options > label:has(input:checked) {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 18%, transparent);
}
.mode-options > label:focus-within,
.semantic-index-toggle:focus-within {
  outline: 3px solid color-mix(in srgb, var(--accent) 35%, transparent);
  outline-offset: 2px;
}
.included-feature {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.included-feature b {
  font-size: 0.875rem;
}
.included-feature span {
  color: var(--muted);
  font-size: 0.8125rem;
}
@container (max-width: 760px) {
  .mode-options {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 620px) {
  .setup-disclosure-body {
    padding: 13px;
  }
  .setup-disclosure > summary {
    padding: 11px 13px;
  }
  .escalation-field,
  .advanced-grid {
    grid-template-columns: 1fr;
  }
}
</style>

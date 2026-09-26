<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { ProviderProfile } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import CorpusTextNoiseSettings from "../CorpusTextNoiseSettings.vue";
import ProviderProfileSelect from "../ProviderProfileSelect.vue";

const props = defineProps<{
  selectedProviderId: string;
  selectedReviewProviderId: string;
  providerProfiles: ProviderProfile[];
  defaultProfileId: string;
  selectedProviderLabel: string;
  selectedProfileModel: string;
  enrichmentMode: "fast" | "deep";
  semanticIndexing: boolean;
  autoCleanText: boolean;
  llmTouchupDuringEnrichment: boolean;
  noiseUnusableThreshold: number;
  llmAssessTextNoise: boolean;
  manualProvider: "ollama" | "openai";
  manualModel: string;
  manualBaseUrl: string;
  manualApiKey: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  "update:selectedProviderId": [value: string];
  "update:selectedReviewProviderId": [value: string];
  "update:enrichmentMode": [value: "fast" | "deep"];
  "update:semanticIndexing": [value: boolean];
  "update:autoCleanText": [value: boolean];
  "update:llmTouchupDuringEnrichment": [value: boolean];
  "update:noiseUnusableThreshold": [value: number];
  "update:llmAssessTextNoise": [value: boolean];
  "update:manualProvider": [value: "ollama" | "openai"];
  "update:manualModel": [value: string];
  "update:manualBaseUrl": [value: string];
  "update:manualApiKey": [value: string];
  manageProviders: [];
}>();

const i18n = useI18nStore();
const manualOpen = ref(false);
const enrichmentSummary = computed(() =>
  [
    props.selectedProviderLabel,
    props.selectedProfileModel,
    props.enrichmentMode === "deep"
      ? i18n.t("pdf_corpus.enrichment_deep")
      : i18n.t("pdf_corpus.enrichment_fast"),
  ]
    .filter(Boolean)
    .join(" · "),
);

function reviewProviderChanged(event: Event) {
  emit(
    "update:selectedReviewProviderId",
    (event.target as HTMLSelectElement).value,
  );
}

function checkboxChanged(
  event: Event,
  name:
    | "update:semanticIndexing"
    | "update:autoCleanText"
    | "update:llmTouchupDuringEnrichment",
) {
  emit(name, (event.target as HTMLInputElement).checked);
}

function manualProviderChanged(event: Event) {
  emit(
    "update:manualProvider",
    (event.target as HTMLSelectElement).value as "ollama" | "openai",
  );
}

function manualInputChanged(
  event: Event,
  name:
    | "update:manualModel"
    | "update:manualBaseUrl"
    | "update:manualApiKey",
) {
  emit(name, (event.target as HTMLInputElement).value);
}
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
      <span>
        <b>{{ i18n.t("pdf_corpus.llm_enrichment_title") }}</b>
        <small>{{ enrichmentSummary }}</small>
      </span>
    </summary>

    <div class="setup-disclosure-body">
      <div class="provider-area">
        <ProviderProfileSelect
          :model-value="props.selectedProviderId"
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
          @update:model-value="emit('update:selectedProviderId', $event)"
          @manage="emit('manageProviders')"
        />

        <label
          v-if="props.selectedProviderId && props.providerProfiles.length > 1"
          class="escalation-field"
          for="pdf-corpus-review-provider"
        >
          <span>
            <b>{{ i18n.t("pdf_corpus.escalation_provider") }}</b>
            <small>{{ i18n.t("pdf_corpus.escalation_provider_help") }}</small>
          </span>
          <select
            id="pdf-corpus-review-provider"
            class="control"
            :value="props.selectedReviewProviderId"
            @change="reviewProviderChanged"
          >
            <option value="">
              {{ i18n.t("pdf_corpus.no_escalation_provider") }}
            </option>
            <option
              v-for="profile in props.providerProfiles"
              :key="profile.id"
              :value="profile.id"
              :disabled="profile.id === props.selectedProviderId"
            >
              {{ profile.name || profile.id }} ·
              {{ profile.model || i18n.t("pdf_corpus.model_not_set") }}
            </option>
          </select>
        </label>
      </div>

      <section
        class="enrichment-strategy"
        aria-labelledby="pdf-corpus-enrichment-mode-title"
      >
        <div class="setup-card-heading">
          <b id="pdf-corpus-enrichment-mode-title">
            {{ i18n.t("pdf_corpus.enrichment_strategy") }}
          </b>
          <small>{{ i18n.t("pdf_corpus.enrichment_strategy_help") }}</small>
        </div>

        <div
          class="mode-options"
          role="radiogroup"
          :aria-label="i18n.t('pdf_corpus.enrichment_strategy')"
        >
          <label>
            <input
              type="radio"
              value="fast"
              :checked="props.enrichmentMode === 'fast'"
              @change="emit('update:enrichmentMode', 'fast')"
            />
            <span>
              <b>{{ i18n.t("pdf_corpus.enrichment_fast") }}</b>
              <small>{{ i18n.t("pdf_corpus.enrichment_fast_help") }}</small>
            </span>
          </label>
          <label>
            <input
              type="radio"
              value="deep"
              :checked="props.enrichmentMode === 'deep'"
              @change="emit('update:enrichmentMode', 'deep')"
            />
            <span>
              <b>{{ i18n.t("pdf_corpus.enrichment_deep") }}</b>
              <small>{{ i18n.t("pdf_corpus.enrichment_deep_help") }}</small>
            </span>
          </label>
        </div>

        <div v-if="props.enrichmentMode === 'deep'" class="included-feature">
          <b>{{ i18n.t("pdf_corpus.semantic_indexing") }}</b>
          <span>{{ i18n.t("pdf_corpus.semantic_indexing_included") }}</span>
        </div>
        <label v-else class="semantic-index-toggle">
          <input
            type="checkbox"
            :checked="props.semanticIndexing"
            @change="checkboxChanged($event, 'update:semanticIndexing')"
          />
          <span>
            <b>{{ i18n.t("pdf_corpus.semantic_indexing") }}</b>
            <small>{{ i18n.t("pdf_corpus.semantic_indexing_help") }}</small>
          </span>
        </label>

        <label class="semantic-index-toggle">
          <input
            type="checkbox"
            :checked="props.autoCleanText"
            @change="checkboxChanged($event, 'update:autoCleanText')"
          />
          <span>
            <b>{{ i18n.t("pdf_corpus.auto_clean_all_records") }}</b>
            <small>{{ i18n.t("pdf_corpus.auto_clean_all_records_help") }}</small>
          </span>
        </label>

        <label class="semantic-index-toggle">
          <input
            type="checkbox"
            :checked="props.llmTouchupDuringEnrichment"
            @change="
              checkboxChanged(
                $event,
                'update:llmTouchupDuringEnrichment',
              )
            "
          />
          <span>
            <b>{{ i18n.t("pdf_corpus.llm_touchup_during_enrichment") }}</b>
            <small>{{ i18n.t("pdf_corpus.llm_touchup_during_enrichment_help") }}</small>
          </span>
        </label>

        <CorpusTextNoiseSettings
          :threshold="props.noiseUnusableThreshold"
          :llm-assist="props.llmAssessTextNoise"
          :disabled="props.disabled"
          @update:threshold="emit('update:noiseUnusableThreshold', $event)"
          @update:llm-assist="emit('update:llmAssessTextNoise', $event)"
        />
      </section>

      <details
        v-if="!props.selectedProviderId"
        :open="manualOpen"
        class="advanced-config"
        @toggle="manualOpen = ($event.currentTarget as HTMLDetailsElement).open"
      >
        <summary>{{ i18n.t("pdf_corpus.manual_provider") }}</summary>
        <p class="help">{{ i18n.t("pdf_corpus.manual_provider_help") }}</p>
        <div class="advanced-grid">
          <label for="pdf-corpus-provider">
            {{ i18n.t("pdf_corpus.provider") }}
          </label>
          <select
            id="pdf-corpus-provider"
            class="control"
            :value="props.manualProvider"
            @change="manualProviderChanged"
          >
            <option value="ollama">Ollama</option>
            <option value="openai">
              {{ i18n.t("pdf_corpus.openai_compatible") }}
            </option>
          </select>

          <label for="pdf-corpus-model">
            {{ i18n.t("pdf_corpus.model") }}
          </label>
          <input
            id="pdf-corpus-model"
            class="control"
            :value="props.manualModel"
            :placeholder="i18n.t('pdf_corpus.provider_default')"
            @input="manualInputChanged($event, 'update:manualModel')"
          />

          <label for="pdf-corpus-url">
            {{ i18n.t("pdf_corpus.base_url") }}
          </label>
          <input
            id="pdf-corpus-url"
            class="control"
            :value="props.manualBaseUrl"
            :placeholder="i18n.t('pdf_corpus.provider_default')"
            @input="manualInputChanged($event, 'update:manualBaseUrl')"
          />

          <label for="pdf-corpus-key">
            {{ i18n.t("pdf_corpus.api_key") }}
          </label>
          <input
            id="pdf-corpus-key"
            class="control"
            type="password"
            autocomplete="off"
            :value="props.manualApiKey"
            :placeholder="i18n.t('pdf_corpus.not_persisted')"
            @input="manualInputChanged($event, 'update:manualApiKey')"
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
  font-size: 0.8125rem;
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
.provider-area,
.enrichment-strategy {
  display: grid;
  gap: 12px;
}
.setup-card-heading {
  display: grid;
  gap: 3px;
}
.setup-card-heading b {
  font-size: 0.8125rem;
}
.setup-card-heading small {
  color: var(--muted);
  font-size: 0.8125rem;
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
.escalation-field b,
.escalation-field small {
  font-size: 0.8125rem;
}
.escalation-field small,
.help {
  color: var(--muted);
  line-height: 1.4;
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
.semantic-index-toggle b,
.included-feature b {
  font-size: 0.875rem;
}
.mode-options small,
.semantic-index-toggle small,
.included-feature span {
  color: var(--muted);
  font-size: 0.8125rem;
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
.advanced-config {
  grid-column: 1 / -1;
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
.advanced-grid label {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 700;
}
.help {
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

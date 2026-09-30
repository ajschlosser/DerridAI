<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import type { ProviderProfile } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import LlmExecutionControl from "../LlmExecutionControl.vue";
import UiButton from "../ui/UiButton.vue";
import UiTooltip from "../ui/UiTooltip.vue";

/** The Record's raw interpretive metadata plus the re-run controls, under the Metadata panel. */
defineProps<{
  busy: boolean;
  hasManifest: boolean;
  profiles: ProviderProfile[];
  providerId: string;
  modelOverride: string;
  familyOptions: Array<{ key: string; label: string }>;
}>();
const emit = defineEmits<{
  clearCache: [];
  editDocumentMetadata: [];
  "update:providerId": [value: string];
  "update:modelOverride": [value: string];
  dirty: [];
  save: [];
  rerun: [];
  requeue: [];
  enrichAgain: [];
}>();
const draft = defineModel<string>("draft", { required: true });
const family = defineModel<string>("family", { required: true });
const i18n = useI18nStore();
</script>

<template>
  <details class="record-data">
    <summary>{{ i18n.t("pdf_corpus.advanced_metadata") }}</summary>
    <p class="help">{{ i18n.t("pdf_corpus.metadata_help") }}</p>
    <UiButton
      size="small"
      button-class="metadata-cache-clear"
      :label="i18n.t('pdf_corpus.clear_metadata_cache')"
      :disabled="busy"
      @click="emit('clearCache')"
    />
    <section v-if="hasManifest" class="document-metadata-launch">
      <div>
        <b>{{ i18n.t("pdf_corpus.document_metadata_defaults") }}</b
        ><span>{{ i18n.t("pdf_corpus.document_metadata_defaults_help") }}</span>
      </div>
      <UiButton
        :label="i18n.t('pdf_corpus.edit_document_metadata')"
        :disabled="busy"
        @click="emit('editDocumentMetadata')"
      />
    </section>

    <LlmExecutionControl
      :model-value="providerId"
      :model-override="modelOverride"
      :profiles="profiles"
      :disabled="busy"
      :task="i18n.t('pdf_corpus.metadata_rerun_provider_help')"
      @update:model-value="(value) => emit('update:providerId', value)"
      @update:model-override="(value) => emit('update:modelOverride', value)"
    /><label class="sr-only" for="pdf-corpus-metadata">{{
      i18n.t("pdf_corpus.interpretive_metadata")
    }}</label
    ><textarea
      id="pdf-corpus-metadata"
      v-model="draft"
      class="metadata-json"
      spellcheck="false"
      @input="emit('dirty')"
    ></textarea>
    <p class="metadata-rerun-consequence">
      {{ i18n.t("pdf_corpus.metadata_rerun_consequence") }}
    </p>
    <div class="data-actions">
      <UiButton
        size="small"
        :label="i18n.t('pdf_corpus.save_metadata')"
        :disabled="busy"
        @click="emit('save')"
      /><label class="rerun-family"
        ><span>{{ i18n.t("pdf_corpus.rerun_family") }}</span
        ><select v-model="family" class="control small">
          <option value="all">{{ i18n.t("pdf_corpus.metadata_family.all") }}</option>
          <option v-for="option in familyOptions" :key="option.key" :value="option.key">
            {{ option.label }}
          </option>
        </select></label
      ><UiTooltip
        :text="i18n.t('pdf_corpus.rerun_metadata_help')"
        trigger-mode="content"
        :content-focusable="busy"
        placement="bottom"
      >
        <UiButton
          size="small"
          :label="i18n.t('pdf_corpus.rerun_metadata')"
          :disabled="busy"
          @click="emit('rerun')"
        /> </UiTooltip
      ><UiTooltip
        :text="i18n.t('pdf_corpus.requeue_metadata_help')"
        trigger-mode="content"
        :content-focusable="busy"
        placement="bottom"
      >
        <UiButton
          size="small"
          variant="soft"
          :label="i18n.t('pdf_corpus.requeue_metadata')"
          :disabled="busy"
          @click="emit('requeue')"
        /> </UiTooltip
      ><UiTooltip
        :text="i18n.t('pdf_corpus.metadata_enrichment_again_help')"
        trigger-mode="content"
        :content-focusable="busy"
        placement="bottom"
      >
        <UiButton
          size="small"
          :label="i18n.t('pdf_corpus.metadata_enrichment_again')"
          :disabled="busy"
          @click="emit('enrichAgain')"
        />
      </UiTooltip>
    </div>
  </details>
</template>

<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import type { ProviderProfile } from "../../api/system";
import { onBeforeUnmount } from "vue";
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
  disclosure: [open: boolean];
}>();
const draft = defineModel<string>("draft", { required: true });
const family = defineModel<string>("family", { required: true });
const i18n = useI18nStore();
function disclosureChanged(event: Event) {
  if (event.target instanceof HTMLDetailsElement) emit("disclosure", event.target.open);
}
onBeforeUnmount(() => emit("disclosure", false));
</script>

<template>
  <details class="record-data" @toggle="disclosureChanged">
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

<style scoped>
.record-data {
  border-top: 1px solid var(--border-subtle);
  padding: 10px 14px;
}
.record-data > summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.document-metadata-launch {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin: 12px 14px;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-subtle);
}
.document-metadata-launch > div {
  display: grid;
  gap: 2px;
  font-size: 0.8125rem;
}
.document-metadata-launch b {
  font-size: 0.875rem;
}
.document-metadata-launch span {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--text-secondary);
}
.metadata-json {
  width: 100%;
  min-height: 230px;
  resize: vertical;
  font:
    12px/1.5 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 8px;
  background: var(--surface-canvas);
  color: var(--text-primary);
  margin: 7px 0;
}
.data-actions {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  align-items: center;
}
.rerun-family {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.8125rem;
}
.rerun-family .control {
  min-width: 190px;
  min-height: 36px;
  font-size: 0.8125rem;
}
.metadata-json {
  font-size: 0.8125rem !important;
}
@media (max-width: 760px) {
  .document-metadata-launch {
    align-items: stretch;
    flex-direction: column;
  }
  .document-metadata-launch :deep(.ui-button) {
    width: 100%;
  }
}
</style>

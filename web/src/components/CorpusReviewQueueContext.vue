<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{
  currentRecordId: string;
  justProcessedRecordId?: string;
  nextRecordId?: string;
}>();

const emit = defineEmits<{
  navigateRecord: [recordId: string];
}>();

const i18n = useI18nStore();
</script>

<template>
  <nav class="queue-context" :aria-label="i18n.t('pdf_corpus.review_queue_context')">
    <span v-if="props.justProcessedRecordId">
      {{ i18n.t("pdf_corpus.just_processed") }}
      <button
        type="button"
        class="text-link"
        :aria-label="
          i18n.tf('pdf_corpus.open_processed_record', {
            record: props.justProcessedRecordId,
          })
        "
        @click="emit('navigateRecord', props.justProcessedRecordId)"
      >
        {{ props.justProcessedRecordId }}
      </button>
    </span>
    <span>
      {{ i18n.t("pdf_corpus.current_record") }}
      <button
        type="button"
        class="text-link"
        :aria-label="
          i18n.tf('pdf_corpus.open_current_record', {
            record: props.currentRecordId,
          })
        "
        @click="emit('navigateRecord', props.currentRecordId)"
      >
        {{ props.currentRecordId }}
      </button>
    </span>
    <span v-if="props.nextRecordId">
      {{ i18n.t("pdf_corpus.next_record_in_queue") }}
      <button
        type="button"
        class="text-link"
        :aria-label="
          i18n.tf('pdf_corpus.open_next_record', {
            record: props.nextRecordId,
          })
        "
        @click="emit('navigateRecord', props.nextRecordId)"
      >
        {{ props.nextRecordId }}
      </button>
    </span>
  </nav>
</template>

<style scoped>
.queue-context {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.queue-context > span {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}
.text-link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--link, var(--accent));
  text-decoration: underline;
  cursor: pointer;
  font: inherit;
}
.text-link:focus-visible {
  outline: 2px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
</style>

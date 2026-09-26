<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { RecordSizingPolicy } from "../types/corpus";
import {
  invalidRecordSizingFields,
  RECORD_SIZING_MIN,
} from "../features/corpus-builder/domain/recordSizing";
const props = defineProps<{ modelValue: RecordSizingPolicy; disabled?: boolean }>();
const emit = defineEmits<{ (event: "update:modelValue", value: RecordSizingPolicy): void }>();
const i18n = useI18nStore();
const low = computed(() =>
  Math.max(
    0,
    Number(props.modelValue.preferred_record_chars) -
      Number(props.modelValue.record_length_tolerance),
  ),
);
const high = computed(
  () =>
    Number(props.modelValue.preferred_record_chars) +
    Number(props.modelValue.record_length_tolerance),
);
const invalid = computed(() => invalidRecordSizingFields(props.modelValue));
function patch(key: keyof RecordSizingPolicy, event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(raw)) return;
  // Never rewrite the reviewer's other fields; an inconsistent policy is
  // surfaced as a warning and blocks the build instead.
  emit("update:modelValue", { ...props.modelValue, [key]: Math.round(raw) });
}
</script>
<template>
  <fieldset class="record-sizing" :disabled="disabled" aria-describedby="record-sizing-help">
    <legend>{{ i18n.t("pdf_corpus.record_sizing.title") }}</legend>
    <p id="record-sizing-help" class="help">{{ i18n.t("pdf_corpus.record_sizing.help") }}</p>
    <div class="primary-grid">
      <label for="corpus-preferred-chars"
        ><span>{{ i18n.t("pdf_corpus.record_sizing.preferred") }}</span
        ><input
          id="corpus-preferred-chars"
          class="control"
          type="number"
          :min="RECORD_SIZING_MIN.preferred_record_chars"
          max="12000"
          step="50"
          :value="modelValue.preferred_record_chars"
          @input="patch('preferred_record_chars', $event)"
        /><small>{{
          i18n.tf("pdf_corpus.record_sizing.preferred_range", {
            low: low.toLocaleString(),
            high: high.toLocaleString(),
          })
        }}</small></label
      >
      <label for="corpus-tolerance-chars"
        ><span>{{ i18n.t("pdf_corpus.record_sizing.tolerance") }}</span
        ><input
          id="corpus-tolerance-chars"
          class="control"
          type="number"
          :min="RECORD_SIZING_MIN.record_length_tolerance"
          max="2000"
          step="25"
          :value="modelValue.record_length_tolerance"
          @input="patch('record_length_tolerance', $event)"
        /><small>{{ i18n.t("pdf_corpus.record_sizing.tolerance_help") }}</small></label
      >
    </div>
    <p v-if="invalid.length" class="sizing-warning" role="alert">
      {{ i18n.t("pdf_corpus.record_sizing.invalid") }}
    </p>
    <details :open="invalid.includes('long_record_chars') || invalid.includes('absolute_record_chars')">
      <summary>{{ i18n.t("pdf_corpus.record_sizing.advanced") }}</summary>
      <div class="advanced-grid">
        <label for="corpus-long-chars"
          ><span>{{ i18n.t("pdf_corpus.record_sizing.long") }}</span
          ><input
            id="corpus-long-chars"
            class="control"
            type="number"
            :min="RECORD_SIZING_MIN.long_record_chars"
            max="24000"
            step="100"
            :value="modelValue.long_record_chars"
            @input="patch('long_record_chars', $event)"
          /><small>{{ i18n.t("pdf_corpus.record_sizing.long_help") }}</small></label
        >
        <label for="corpus-absolute-chars"
          ><span>{{ i18n.t("pdf_corpus.record_sizing.absolute") }}</span
          ><input
            id="corpus-absolute-chars"
            class="control"
            type="number"
            :min="RECORD_SIZING_MIN.absolute_record_chars"
            max="48000"
            step="100"
            :value="modelValue.absolute_record_chars"
            @input="patch('absolute_record_chars', $event)"
          /><small>{{ i18n.t("pdf_corpus.record_sizing.absolute_help") }}</small></label
        >
      </div>
    </details>
  </fieldset>
</template>
<style scoped>
.sizing-warning {
  margin: 8px 0 0;
  color: var(--status-warning-text, var(--text));
  font-size: var(--text-sm, 0.875rem);
}
.record-sizing {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  display: grid;
  gap: 8px;
  background: var(--card);
  min-inline-size: 0;
}
.record-sizing legend {
  padding-inline: 4px;
  font-size: 0.8125rem;
  font-weight: 800;
}
.help {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.primary-grid,
.advanced-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.record-sizing label {
  display: grid;
  gap: 4px;
  font-size: 0.8125rem;
  font-weight: 700;
}
.record-sizing small {
  font-size: 0.8125rem;
  line-height: 1.35;
  color: var(--muted);
  font-weight: 500;
}
.record-sizing details {
  border-block-start: 1px solid var(--line);
  padding-block-start: 7px;
}
.record-sizing summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
  color: var(--muted);
}
.advanced-grid {
  margin-block-start: 8px;
}
@media (max-width: 720px) {
  .primary-grid,
  .advanced-grid {
    grid-template-columns: 1fr;
  }
}
</style>

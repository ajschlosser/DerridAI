<script setup lang="ts">
import { useId } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { AutonomousPolicy } from "../api/pdfCorpus";

// The settings for hands-free mode. Nobody reviews the records in this mode, so these are the rules that decide for
// them; the page says so plainly, and what the rules could not settle is reported afterwards.
const props = withDefaults(
  defineProps<{ modelValue: AutonomousPolicy; disabled?: boolean; showEnable?: boolean }>(),
  { disabled: false, showEnable: true },
);
const emit = defineEmits<{ "update:modelValue": [value: AutonomousPolicy] }>();
const i18n = useI18nStore();
const id = useId();
const set = <K extends keyof AutonomousPolicy>(key: K, value: AutonomousPolicy[K]) =>
  emit("update:modelValue", { ...props.modelValue, [key]: value });
const pct = (value: number) => `${Math.round(value * 100)}%`;
</script>

<template>
  <div class="hands-free">
    <p class="hands-free-note">{{ i18n.t("pdf_corpus.hands_free_note") }}</p>
    <label v-if="showEnable" class="hf-check"
      ><input
        type="checkbox"
        :checked="modelValue.enabled"
        :disabled="disabled"
        @change="set('enabled', ($event.target as HTMLInputElement).checked)"
      /><span
        ><b>{{ i18n.t("pdf_corpus.hands_free_enable") }}</b></span
      ></label
    >
    <fieldset class="hf-grid" :disabled="disabled || (showEnable && !modelValue.enabled)">
      <label class="hf-field" :for="`${id}-passes`"
        ><span>{{ i18n.t("pdf_corpus.hands_free_passes") }}</span>
        <input
          :id="`${id}-passes`"
          class="control"
          type="number"
          min="0"
          max="3"
          :value="modelValue.passes"
          @input="
            set(
              'passes',
              Math.max(0, Math.min(3, Number(($event.target as HTMLInputElement).value) || 0)),
            )
          "
        />
        <small>{{ i18n.t("pdf_corpus.hands_free_passes_help") }}</small></label
      >
      <label class="hf-field" :for="`${id}-conf`"
        ><span>{{
          i18n.tf("pdf_corpus.hands_free_confidence", { percent: pct(modelValue.min_confidence) })
        }}</span>
        <input
          :id="`${id}-conf`"
          type="range"
          min="0.5"
          max="0.99"
          step="0.01"
          :value="modelValue.min_confidence"
          @input="set('min_confidence', Number(($event.target as HTMLInputElement).value))"
        />
        <small>{{ i18n.t("pdf_corpus.hands_free_confidence_help") }}</small></label
      >
      <label class="hf-field" :for="`${id}-unresolved`"
        ><span>{{ i18n.t("pdf_corpus.hands_free_unresolved") }}</span>
        <select
          :id="`${id}-unresolved`"
          class="control"
          :value="modelValue.unresolved"
          @change="
            set(
              'unresolved',
              ($event.target as HTMLSelectElement).value as AutonomousPolicy['unresolved'],
            )
          "
        >
          <option value="best_guess">{{ i18n.t("pdf_corpus.hands_free_best_guess") }}</option>
          <option value="leave">{{ i18n.t("pdf_corpus.hands_free_leave") }}</option>
        </select></label
      >
      <label class="hf-check"
        ><input
          type="checkbox"
          :checked="modelValue.accept_records"
          @change="set('accept_records', ($event.target as HTMLInputElement).checked)"
        /><span
          ><b>{{ i18n.t("pdf_corpus.hands_free_accept") }}</b></span
        ></label
      >
      <label class="hf-check"
        ><input
          type="checkbox"
          :checked="modelValue.publish"
          @change="set('publish', ($event.target as HTMLInputElement).checked)"
        /><span
          ><b>{{ i18n.t("pdf_corpus.hands_free_publish") }}</b
          ><small>{{ i18n.t("pdf_corpus.hands_free_publish_help") }}</small></span
        ></label
      >
    </fieldset>
  </div>
</template>

<style scoped>
.hands-free {
  display: grid;
  gap: var(--space-3);
}
.hands-free-note {
  margin: 0;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--tone-warn-border);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-base);
  line-height: var(--lh-normal);
}
.hf-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3) var(--space-4);
  margin: 0;
  padding: 0;
  border: 0;
  min-inline-size: 0;
}
.hf-field {
  display: grid;
  gap: var(--space-1);
  align-content: start;
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}
.hf-field small,
.hf-check small {
  display: block;
  color: var(--text-tertiary);
  font-weight: var(--fw-medium);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.hf-check {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
}
.hf-check input {
  inline-size: 18px;
  block-size: 18px;
  margin-top: 2px;
  flex: none;
}
.control {
  inline-size: 100%;
  min-block-size: var(--control-height);
}
fieldset:disabled {
  opacity: 0.6;
}
@media (max-width: 720px) {
  .hf-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

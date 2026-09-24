<script setup lang="ts">
import { useId } from "vue";
import { useI18nStore } from "../stores/i18n";

withDefaults(defineProps<{ threshold: number; llmAssist: boolean; disabled?: boolean }>(), {
  disabled: false,
});
const emit = defineEmits<{ "update:threshold": [value: number]; "update:llmAssist": [value: boolean] }>();
const i18n = useI18nStore();
const id = useId();
const percent = (value: number) => `${Math.round(value)}%`;
</script>

<template>
  <fieldset class="text-noise" :disabled="disabled">
    <legend>{{ i18n.t("pdf_corpus.text_noise.title") }}</legend>
    <p>
      {{
        i18n.t("pdf_corpus.text_noise.help")
      }}
    </p>
    <label class="noise-field" :for="`${id}-threshold`">
      <span>{{
        i18n.tf("pdf_corpus.text_noise.threshold", {
          percent: percent(threshold),
        })
      }}</span>
      <input
        :id="`${id}-threshold`"
        type="range"
        min="0"
        max="100"
        step="1"
        :value="threshold"
        :aria-valuemin="0"
        :aria-valuemax="100"
        :aria-valuenow="Math.round(threshold)"
        :aria-valuetext="percent(threshold)"
        @input="emit('update:threshold', Number(($event.target as HTMLInputElement).value))"
      />
      <small>{{
        i18n.t("pdf_corpus.text_noise.threshold_help")
      }}</small>
    </label>
    <label class="noise-check">
      <input
        type="checkbox"
        :checked="llmAssist"
        @change="emit('update:llmAssist', ($event.target as HTMLInputElement).checked)"
      />
      <span>
        <b>{{ i18n.t("pdf_corpus.text_noise.llm") }}</b>
        <small>{{
          i18n.t("pdf_corpus.text_noise.llm_help")
        }}</small>
      </span>
    </label>
  </fieldset>
</template>

<style scoped>
.text-noise {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  display: grid;
  gap: 10px;
  background: var(--card);
}
legend {
  font-size: 0.8125rem;
  font-weight: 800;
  padding-inline: 4px;
}
p,
.noise-field small,
.noise-check small {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
  font-weight: 500;
}
.noise-field {
  display: grid;
  gap: 6px;
  font-size: 0.8125rem;
  font-weight: 700;
}
.noise-field input[type="range"] {
  inline-size: 100%;
  min-block-size: 24px;
}
.noise-check {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.noise-check input {
  inline-size: 18px;
  block-size: 18px;
  margin-top: 2px;
  flex: none;
}
.noise-check span {
  display: grid;
  gap: 2px;
}
fieldset:disabled {
  opacity: 0.6;
}
</style>

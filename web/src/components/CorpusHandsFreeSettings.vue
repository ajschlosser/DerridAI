<script setup lang="ts">
import { useId } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { AutonomousPolicy } from "../api/pdfCorpus";

// The settings for hands-free mode. Nobody reviews the records in this mode, so these are the rules that decide for
// them; the page says so plainly, and what the rules could not settle is reported afterwards.
const props = withDefaults(defineProps<{ modelValue: AutonomousPolicy; disabled?: boolean; showEnable?: boolean }>(), { disabled: false, showEnable: true });
const emit = defineEmits<{ "update:modelValue": [value: AutonomousPolicy] }>();
const i18n = useI18nStore();
const id = useId();
const set = <K extends keyof AutonomousPolicy>(key: K, value: AutonomousPolicy[K]) => emit("update:modelValue", { ...props.modelValue, [key]: value });
const pct = (value: number) => `${Math.round(value * 100)}%`;
</script>

<template>
  <div class="hands-free">
    <p class="hands-free-note">{{ i18n.t("pdf_corpus.hands_free_note", "No one reviews the records in this mode. The rules below decide, every value the model proposes stays labelled as the model's, and anything the rules cannot settle is left for you and listed afterwards.") }}</p>
    <label v-if="showEnable" class="hf-check"><input type="checkbox" :checked="modelValue.enabled" :disabled="disabled" @change="set('enabled', ($event.target as HTMLInputElement).checked)"><span><b>{{ i18n.t("pdf_corpus.hands_free_enable", "Run hands-free after the build") }}</b></span></label>
    <fieldset class="hf-grid" :disabled="disabled || (showEnable && !modelValue.enabled)">
      <label class="hf-field" :for="`${id}-passes`"><span>{{ i18n.t("pdf_corpus.hands_free_passes", "Extra enrichment passes") }}</span>
        <input :id="`${id}-passes`" class="control" type="number" min="0" max="3" :value="modelValue.passes" @input="set('passes', Math.max(0, Math.min(3, Number(($event.target as HTMLInputElement).value) || 0)))">
        <small>{{ i18n.t("pdf_corpus.hands_free_passes_help", "Each pass can use what the earlier ones found. 0 to 3.") }}</small></label>
      <label class="hf-field" :for="`${id}-conf`"><span>{{ i18n.tf("pdf_corpus.hands_free_confidence", "Take a proposal at {percent} confidence or more", { percent: pct(modelValue.min_confidence) }) }}</span>
        <input :id="`${id}-conf`" type="range" min="0.5" max="0.99" step="0.01" :value="modelValue.min_confidence" @input="set('min_confidence', Number(($event.target as HTMLInputElement).value))">
        <small>{{ i18n.t("pdf_corpus.hands_free_confidence_help", "The model's own stated confidence. Higher is stricter.") }}</small></label>
      <label class="hf-field" :for="`${id}-unresolved`"><span>{{ i18n.t("pdf_corpus.hands_free_unresolved", "When a field is still unsure") }}</span>
        <select :id="`${id}-unresolved`" class="control" :value="modelValue.unresolved" @change="set('unresolved', ($event.target as HTMLSelectElement).value as AutonomousPolicy['unresolved'])">
          <option value="best_guess">{{ i18n.t("pdf_corpus.hands_free_best_guess", "Take the model's best guess anyway") }}</option>
          <option value="leave">{{ i18n.t("pdf_corpus.hands_free_leave", "Leave it for me") }}</option>
        </select></label>
      <label class="hf-check"><input type="checkbox" :checked="modelValue.accept_records" @change="set('accept_records', ($event.target as HTMLInputElement).checked)"><span><b>{{ i18n.t("pdf_corpus.hands_free_accept", "Accept records with nothing left waiting") }}</b></span></label>
      <label class="hf-check"><input type="checkbox" :checked="modelValue.publish" @change="set('publish', ($event.target as HTMLInputElement).checked)"><span><b>{{ i18n.t("pdf_corpus.hands_free_publish", "Publish when every record is accepted") }}</b><small>{{ i18n.t("pdf_corpus.hands_free_publish_help", "Off by default. Publishing is not undone by reviewing later.") }}</small></span></label>
    </fieldset>
  </div>
</template>

<style scoped>
.hands-free { display: grid; gap: 12px; }
.hands-free-note { margin: 0; padding: 10px 12px; border: 1px solid var(--tone-warn-border); border-radius: 10px; background: var(--tone-warn-bg); color: var(--tone-warn-fg); font-size: 0.875rem; line-height: 1.5; }
.hf-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; margin: 0; padding: 0; border: 0; min-inline-size: 0; }
.hf-field { display: grid; gap: 5px; align-content: start; font-size: 0.8125rem; font-weight: 700; }
.hf-field small, .hf-check small { display: block; color: var(--muted); font-weight: 500; font-size: 0.8125rem; line-height: 1.45; }
.hf-check { display: flex; gap: 10px; align-items: flex-start; }
.hf-check input { inline-size: 18px; block-size: 18px; margin-top: 2px; flex: none; }
.control { inline-size: 100%; min-block-size: 42px; }
fieldset:disabled { opacity: 0.6; }
@media (max-width: 720px) { .hf-grid { grid-template-columns: minmax(0, 1fr); } }
</style>

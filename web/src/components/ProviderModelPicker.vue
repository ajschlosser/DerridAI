<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { useI18nStore } from "../stores/i18n";
import { modelMatchesKind, type DiscoveredModel } from "../domain/providerModels";
import UiButton from "./ui/UiButton.vue";
import UiDialog from "./ui/UiDialog.vue";

// A model field that can be typed into, or chosen from what the endpoint reports. "View models" opens a searchable
// list showing each model's size and quantization, so a person can tell the 4B from the 14B without leaving the page.
// The list is a dialog of ordinary buttons (name, details, "Use model") in a labelled list, with the match count
// announced as the filter changes, so it works with a keyboard and a screen reader.
const props = withDefaults(defineProps<{
  profileName: string;
  modelValue: string;
  models?: DiscoveredModel[];
  kind?: string;
  disabled?: boolean;
  placeholder?: string;
  busy?: boolean;
}>(), { models: () => [], kind: "any", disabled: false, placeholder: "", busy: false });
const emit = defineEmits<{ "update:modelValue": [value: string]; discover: [] }>();
const i18n = useI18nStore();
const open = ref(false);
const query = ref("");
const inputId = useId();
const datalistId = useId();
const input = ref<HTMLInputElement | null>(null);

const usable = computed(() => props.models.filter(model => model.name && modelMatchesKind(model.name, props.kind)));
const shown = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  return usable.value.filter(model => String(model.name).toLocaleLowerCase().includes(needle));
});
const detail = (model: DiscoveredModel) => [model.parameter_size, model.quantization_level].filter(Boolean).join(" · ") || i18n.t("providers.model_no_details", "No size reported");
function openList() {
  query.value = "";
  open.value = true;
  if (!props.models.length) emit("discover");
}
function choose(name: string) {
  emit("update:modelValue", name);
  open.value = false;
  // Return focus to where the person was, so the choice is visible in the field it filled.
  queueMicrotask(() => input.value?.focus());
}
</script>

<template>
  <div class="provider-model-field">
    <label class="field-label" :for="inputId">{{ i18n.t("providers.model", "Model") }}</label>
    <div class="picker-row">
      <input :id="inputId" ref="input" class="control" :value="modelValue" :list="datalistId" :disabled="disabled" :placeholder="placeholder" autocomplete="off" @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)">
      <datalist :id="datalistId"><option v-for="model in usable" :key="model.name" :value="model.name"></option></datalist>
      <UiButton :label="usable.length ? i18n.tf('providers.view_models_count', 'View models ({count})', { count: usable.length }) : i18n.t('providers.view_models', 'View models')" :disabled="busy" @click="openList" />
    </div>
    <UiDialog v-if="open" size="medium" :title="i18n.t('providers.available_models', 'Available models')" :description="i18n.tf('providers.models_discovered', '{name} · {count} discovered', { name: profileName, count: usable.length })" :close-label="i18n.t('ui.close', 'Close')" @close="open = false">
      <div class="model-search">
        <label :for="`${inputId}-search`">{{ i18n.t("providers.filter_models", "Filter models") }}</label>
        <input :id="`${inputId}-search`" v-model="query" class="control" type="search" autocomplete="off" autofocus>
        <p class="model-count" role="status" aria-live="polite">{{ i18n.tf("providers.models_match", "{count} models match", { count: shown.length }) }}</p>
      </div>
      <p v-if="busy" class="model-empty" role="status">{{ i18n.t("providers.discovering", "Asking the endpoint for its models…") }}</p>
      <ul v-else-if="shown.length" class="model-list" :aria-label="i18n.t('providers.available_models', 'Available models')">
        <li v-for="model in shown" :key="model.name">
          <button type="button" class="model-row" :aria-current="model.name === modelValue ? 'true' : undefined" @click="choose(String(model.name))">
            <span class="model-row-main"><b>{{ model.name }}</b><small>{{ detail(model) }}</small></span>
            <span class="model-row-use">{{ model.name === modelValue ? i18n.t("providers.model_in_use", "In use") : i18n.t("providers.use_model", "Use model") }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="model-empty">{{ i18n.t("providers.no_models_match", "No models match this filter.") }}</p>
    </UiDialog>
  </div>
</template>

<style scoped>
/* Not "provider-model-picker": the global stylesheet has a two-column rule under that name from the old page. */
.provider-model-field { display: grid; gap: 5px; margin-block-end: 10px; min-inline-size: 0; }
.field-label { font-size: 0.75rem; color: var(--muted); font-weight: 730; }
.picker-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: start; }
.control { inline-size: 100%; min-block-size: 42px; }
.model-search { display: grid; gap: 6px; margin-block-end: 12px; }
.model-search label { font-size: 0.8125rem; font-weight: 700; }
.model-count { margin: 0; font-size: 0.8125rem; color: var(--muted); }
.model-list { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; max-block-size: min(420px, 55vh); overflow: auto; overscroll-behavior: auto; }
.model-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; inline-size: 100%; min-block-size: 48px; padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--text); font: inherit; text-align: start; cursor: pointer; }
.model-row:hover { background: var(--soft); }
.model-row:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; }
.model-row[aria-current="true"] { border-color: var(--accent-fg); }
.model-row-main { display: grid; gap: 2px; min-inline-size: 0; }
.model-row-main b { overflow-wrap: anywhere; font-size: 0.875rem; }
.model-row-main small { color: var(--muted); font-size: 0.8125rem; }
.model-row-use { flex: none; color: var(--accent-fg); font-size: 0.8125rem; font-weight: 700; }
.model-empty { margin: 0; padding: 16px 4px; color: var(--muted); }
@media (max-width: 560px) { .picker-row { grid-template-columns: minmax(0, 1fr); } }
</style>

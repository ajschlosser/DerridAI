<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ProviderProfile } from "../api/system";
import { systemApi } from "../api/system";
import { useI18nStore } from "../stores/i18n";
const props = defineProps<{
  modelValue: string;
  modelOverride?: string;
  profiles: ProviderProfile[];
  disabled?: boolean;
  task?: string;
  concurrencyRisk?: boolean;
  activeRequests?: number;
  concurrencyLimit?: number;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: string];
  "update:modelOverride": [value: string];
}>();
const i18n = useI18nStore();
const selected = computed(() => props.profiles.find((p) => p.id === props.modelValue) || null);
const models = ref<string[]>([]);
const loadingModels = ref(false);
const modelError = ref("");
const effectiveModel = computed(() => props.modelOverride || String(selected.value?.model || ""));
async function loadModels() {
  models.value = [];
  modelError.value = "";
  const profile = selected.value;
  if (!profile) return;
  loadingModels.value = true;
  try {
    const result = await systemApi.researcherProviderStatus({
      id: profile.id,
      type: profile.type,
      base_url: profile.base_url,
    });
    models.value = (result.models || []).map((item) => String(item.name || "")).filter(Boolean);
    const current = effectiveModel.value;
    if (current && !models.value.includes(current)) models.value.unshift(current);
  } catch (exc) {
    modelError.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loadingModels.value = false;
  }
}
watch(
  () => props.modelValue,
  () => {
    void loadModels();
  },
  { immediate: true },
);
</script>
<template>
  <section
    class="llm-execution"
    role="group"
    :aria-label="i18n.t('pdf_corpus.llm_execution')"
  >
    <div class="llm-notice">
      <div>
        <b>{{ i18n.t("pdf_corpus.llm_will_be_used") }}</b
        ><small>{{
          task ||
          i18n.t("pdf_corpus.llm_choose_profile_help")
        }}</small>
      </div>
    </div>
    <label
      ><span>{{ i18n.t("pdf_corpus.provider_profile") }}</span
      ><select
        class="control"
        :value="modelValue"
        :disabled="disabled || !profiles.length"
        @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>
          {{ i18n.t("pdf_corpus.choose_provider_profile") }}
        </option>
        <option v-for="profile in profiles" :key="profile.id" :value="profile.id">
          {{ profile.name || profile.id }}
        </option>
      </select></label
    ><label v-if="selected"
      ><span>{{ i18n.t("pdf_corpus.model_for_action") }}</span
      ><input
        class="control"
        :value="effectiveModel"
        :list="`llm-models-${selected.id}`"
        :disabled="disabled"
        :placeholder="
          loadingModels
            ? i18n.t('pdf_corpus.loading_models')
            : i18n.t('pdf_corpus.custom_model_allowed')
        "
        @input="emit('update:modelOverride', ($event.target as HTMLInputElement).value)"
      /><datalist :id="`llm-models-${selected.id}`">
        <option v-for="model in models" :key="model" :value="model" /></datalist
      ><small>{{
        i18n.t("pdf_corpus.model_override_help")
      }}</small></label
    ><small v-if="modelError" class="model-error" role="status">{{ modelError }}</small>
    <p v-if="concurrencyRisk && selected?.type === 'ollama'" class="capacity-warning" role="status">
      {{
        i18n.tf("pdf_corpus.ollama_concurrency_warning", { active: activeRequests ?? concurrencyLimit ?? 1, limit: concurrencyLimit ?? 1 })
      }}
    </p>
  </section>
</template>
<style scoped>
.llm-execution {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(220px, 1fr) minmax(220px, 1fr);
  gap: 10px 14px;
  align-items: end;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.llm-notice div,
.llm-execution label {
  display: grid;
  gap: 3px;
}
.llm-notice b,
.llm-execution label > span {
  font-size: 0.8125rem;
}
.llm-notice small,
.model-error {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.35;
}
.control {
  min-height: 42px;
}
.capacity-warning {
  grid-column: 1/-1;
  margin: 0;
  padding: 9px 10px;
  border: 1px solid var(--warning, #a16207);
  border-radius: 8px;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.model-error {
  grid-column: 1/-1;
}
.control:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 1100px) {
  .llm-execution {
    grid-template-columns: 1fr;
  }
  .capacity-warning,
  .model-error {
    grid-column: auto;
  }
}
</style>

<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import type { ProviderProfile } from "../../api/system";
import { PROVIDER_BULK_FIELDS } from "../../domain/providerBulkFields";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{ profiles: ProviderProfile[] }>();
const emit = defineEmits<{ apply: [ids: string[], values: Record<string, unknown>] }>();
const i18n = useI18nStore();
const selected = reactive(new Set<string>());
const target = ref<"all" | "selected">("all");
const values = reactive<Record<string, string>>({});

const fieldLabels: Record<string, [string, string]> = {
  max_concurrent_requests: ["providers.concurrency", "Max concurrent requests"],
  num_ctx: ["providers.context", "Context tokens"],
  num_predict: ["providers.max_output", "Max output tokens"],
  metadata_num_predict: ["providers.metadata_output", "Metadata output tokens"],
  temperature: ["providers.temperature", "Temperature"],
  top_p: ["providers.top_p", "Top P"],
  top_k: ["providers.top_k", "Top K"],
  min_p: ["providers.min_p", "Min P"],
  repeat_penalty: ["providers.repeat_penalty", "Repeat penalty"],
  seed: ["providers.seed", "Seed"],
  think: ["providers.think", "Think"],
  keep_alive: ["providers.keep_alive", "Keep alive"],
  mirostat: ["providers.mirostat", "Mirostat"],
  mirostat_eta: ["providers.mirostat_eta", "Mirostat eta"],
  mirostat_tau: ["providers.mirostat_tau", "Mirostat tau"],
};

function toggle(id: string, on: boolean) {
  if (on) selected.add(id);
  else selected.delete(id);
}

const parsedValues = computed(() => {
  const out: Record<string, unknown> = {};
  for (const field of PROVIDER_BULK_FIELDS) {
    const raw = values[field.key];
    if (raw == null || String(raw).trim() === "") continue;
    out[field.key] = field.input === "number" ? Number(raw) : raw;
  }
  return out;
});

function apply() {
  const ids =
    target.value === "all"
      ? props.profiles.map((profile) => profile.id)
      : props.profiles.filter((profile) => selected.has(profile.id)).map((profile) => profile.id);
  if (!ids.length || !Object.keys(parsedValues.value).length) return;
  emit("apply", ids, { ...parsedValues.value });
}
</script>

<template>
  <section class="provider-bulk" aria-labelledby="provider-bulk-title">
    <div>
      <p class="eyebrow">{{ i18n.t("providers.bulk_apply") }}</p>
      <h2 id="provider-bulk-title">{{ i18n.t("providers.bulk_apply_title") }}</h2>
      <p>{{ i18n.t("providers.bulk_apply_help") }}</p>
    </div>
    <fieldset class="provider-bulk-target">
      <legend>{{ i18n.t("providers.bulk_target") }}</legend>
      <label><input v-model="target" type="radio" value="all" /> {{ i18n.t("providers.apply_to_all") }}</label>
      <label><input v-model="target" type="radio" value="selected" /> {{ i18n.t("providers.apply_to_selected") }}</label>
    </fieldset>
    <div v-if="target === 'selected'" class="provider-bulk-pick">
      <label v-for="profile in profiles" :key="profile.id">
        <input type="checkbox" :checked="selected.has(profile.id)" @change="toggle(profile.id, ($event.target as HTMLInputElement).checked)" />
        {{ profile.name || profile.id }}
      </label>
    </div>
    <div class="provider-bulk-fields">
      <label v-for="field in PROVIDER_BULK_FIELDS" :key="field.key" class="field">
        <span>{{ i18n.t(fieldLabels[field.key]?.[0] || `providers.${field.key}`, fieldLabels[field.key]?.[1] || field.key) }}</span>
        <select v-if="field.input === 'select'" class="control" :value="values[field.key] || ''" @change="values[field.key] = ($event.target as HTMLSelectElement).value">
          <option value="">{{ i18n.t("providers.leave_unchanged") }}</option>
          <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <input
          v-else
          class="control"
          :type="field.input === 'number' ? 'number' : 'text'"
          :min="field.min"
          :max="field.max"
          :step="field.step"
          :placeholder="i18n.t('providers.leave_unchanged')"
          :value="values[field.key] || ''"
          @input="values[field.key] = ($event.target as HTMLInputElement).value"
        />
      </label>
    </div>
    <button type="button" class="btn primary" :disabled="!Object.keys(parsedValues).length || (target === 'selected' && !selected.size)" @click="apply">
      {{ i18n.t("providers.apply_values") }}
    </button>
  </section>
</template>

<style scoped>
.provider-bulk {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid var(--line);
  background: var(--raised);
}
.provider-bulk h2 {
  margin: 4px 0 0;
  font-size: 1.05rem;
}
.provider-bulk > div:first-child p:not(.eyebrow) {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-fg);
}
.provider-bulk-target {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 18px;
  margin: 0;
  padding: 0;
  border: 0;
}
.provider-bulk-target legend {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
.provider-bulk-pick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}
.provider-bulk-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.field {
  display: grid;
  gap: 6px;
}
.field > span {
  font-size: 0.75rem;
  font-weight: 700;
}
</style>

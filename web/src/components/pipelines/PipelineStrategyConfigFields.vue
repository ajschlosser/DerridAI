<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import {
  pipelineConfigHelp,
  pipelineConfigLabel,
  pipelineConfigOptionLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";
import type { PipelineStage, PipelineStrategy } from "../../types/pipelines";

const props = defineProps<{
  stage: PipelineStage;
  strategy: PipelineStrategy | null;
}>();

const emit = defineEmits<{
  updateConfig: [key: string, raw: string | boolean, rule: Record<string, unknown>];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const configProperties = computed(() => {
  const schema = props.strategy?.config_schema;
  if (!schema || typeof schema !== "object") {
    return [] as Array<[string, Record<string, unknown>]>;
  }
  const properties = (schema as { properties?: unknown }).properties;
  if (!properties || typeof properties !== "object" || Array.isArray(properties)) {
    return [] as Array<[string, Record<string, unknown>]>;
  }
  return Object.entries(properties as Record<string, Record<string, unknown>>);
});

function configValue(key: string, rule: Record<string, unknown>) {
  if (props.stage.config[key] !== undefined) return props.stage.config[key];
  if (rule.default !== undefined) return rule.default;
  return "";
}

function enumValues(rule: Record<string, unknown>) {
  return Array.isArray(rule.enum) ? rule.enum.map(String) : null;
}
</script>

<template>
  <div v-if="configProperties.length" class="config-grid">
    <label v-for="[key, rule] in configProperties" :key="key">
      <span class="config-label">
        {{ pipelineConfigLabel(key, t) }}
        <UiTooltip
          :text="pipelineConfigHelp(key, t)"
          :label="t('pipelines.explain_setting', 'Explain this setting')"
        />
      </span>
      <input
        v-if="rule.type === 'number' || rule.type === 'integer'"
        class="control"
        type="number"
        :step="rule.type === 'integer' ? 1 : 'any'"
        :min="typeof rule.minimum === 'number' ? rule.minimum : undefined"
        :max="typeof rule.maximum === 'number' ? rule.maximum : undefined"
        :value="configValue(key, rule)"
        @input="emit('updateConfig', key, ($event.target as HTMLInputElement).value, rule)"
      />
      <select
        v-else-if="rule.type === 'boolean'"
        class="control"
        :value="String(configValue(key, rule))"
        @change="
          emit('updateConfig', key, ($event.target as HTMLSelectElement).value === 'true', rule)
        "
      >
        <option value="true">{{ t("common.yes", "Yes") }}</option>
        <option value="false">{{ t("common.no", "No") }}</option>
      </select>
      <select
        v-else-if="enumValues(rule)"
        class="control"
        :value="String(configValue(key, rule))"
        @change="emit('updateConfig', key, ($event.target as HTMLSelectElement).value, rule)"
      >
        <option v-for="option in enumValues(rule)" :key="option" :value="option">
          {{ pipelineConfigOptionLabel(key, option, t) }}
        </option>
      </select>
      <input
        v-else
        class="control"
        :value="String(configValue(key, rule))"
        @input="emit('updateConfig', key, ($event.target as HTMLInputElement).value, rule)"
      />
    </label>
  </div>
  <p v-else class="no-config">
    {{ t("pipelines.no_stage_settings", "This stage has no configurable parameters.") }}
  </p>
</template>

<style scoped>
.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.config-grid label {
  display: grid;
  gap: 5px;
}
.config-grid label > span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.config-label {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.no-config {
  margin: 0;
  color: var(--muted);
  font-size: 0.76rem;
}
@media (max-width: 680px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>

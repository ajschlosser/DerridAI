<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { ProviderProfile } from "../../api/system";
import { MODEL_KINDS } from "../../domain/providerModels";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";

// Capacity and generation parameters: the details most people never change, so
// they stay folded until asked for.
defineProps<{ profile: ProviderProfile; sharedLimit: number; sharedEndpoint: boolean }>();
const emit = defineEmits<{ update: [field: string, value: unknown] }>();
const i18n = useI18nStore();
function numeric(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
</script>

<template>
  <div class="provider-tuning">
    <details class="provider-more">
      <summary>{{ i18n.t("providers.group_capacity") }}</summary>
      <div class="provider-fields three">
        <label class="field"
          ><span
            >{{ i18n.t("providers.concurrency") }}
            <UiTooltip :text="i18n.t('providers.concurrency_help')" /></span
          ><input
            class="control"
            type="number"
            min="1"
            max="64"
            :value="sharedLimit"
            @input="
              emit(
                'update',
                'max_concurrent_requests',
                Math.max(1, Math.min(64, numeric(($event.target as HTMLInputElement).value, 1))),
              )
            "
          /><small v-if="sharedEndpoint">{{ i18n.t("providers.shared_endpoint") }}</small></label
        >
        <label class="field"
          ><span
            >{{ i18n.t("providers.context") }}
            <UiTooltip :text="i18n.t('help.glossary.context_window.definition')" /></span
          ><input
            class="control"
            type="number"
            min="512"
            :value="profile.num_ctx || 16384"
            @input="
              emit('update', 'num_ctx', numeric(($event.target as HTMLInputElement).value, 16384))
            "
        /></label>
        <label class="field"
          ><span
            >{{ i18n.t("providers.max_output") }}
            <UiTooltip :text="i18n.t('providers.max_output_help')" /></span
          ><input
            class="control"
            type="number"
            min="16"
            :value="profile.num_predict || 4096"
            @input="
              emit(
                'update',
                'num_predict',
                numeric(($event.target as HTMLInputElement).value, 4096),
              )
            "
        /></label>
      </div>
    </details>
    <details class="provider-more">
      <summary>{{ i18n.t("providers.advanced") }}</summary>
      <div class="provider-fields three">
        <label v-if="profile.type === 'openai'" class="field"
          ><span
            >{{ i18n.t("providers.model_kind") }}
            <UiTooltip :text="i18n.t('providers.model_kind_help')" /></span
          ><select
            class="control"
            :value="profile.model_kind || 'any'"
            @change="emit('update', 'model_kind', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="kind in MODEL_KINDS" :key="kind" :value="kind">
              {{ i18n.t(`providers.kind_${kind}`, kind) }}
            </option>
          </select></label
        >
        <label class="field"
          ><span
            >{{ i18n.t("providers.temperature") }}
            <UiTooltip :text="i18n.t('help.glossary.temperature.definition')" /></span
          ><input
            class="control"
            type="number"
            min="0"
            max="2"
            step="0.01"
            :value="profile.temperature ?? 0"
            @input="
              emit('update', 'temperature', numeric(($event.target as HTMLInputElement).value, 0))
            "
        /></label>
        <label class="field"
          ><span
            >{{ i18n.t("providers.top_p") }}
            <UiTooltip :text="i18n.t('help.glossary.top_p.definition')" /></span
          ><input
            class="control"
            type="number"
            min="0"
            max="1"
            step="0.01"
            :value="profile.top_p ?? 1"
            @input="emit('update', 'top_p', numeric(($event.target as HTMLInputElement).value, 1))"
        /></label>
        <label v-if="profile.type === 'ollama'" class="field"
          ><span
            >{{ i18n.t("providers.top_k") }}
            <UiTooltip :text="i18n.t('providers.top_k_help')" /></span
          ><input
            class="control"
            type="number"
            min="0"
            :value="profile.top_k ?? 0"
            @input="emit('update', 'top_k', numeric(($event.target as HTMLInputElement).value, 0))"
        /></label>
        <label class="field"
          ><span
            >{{ i18n.t("providers.seed") }}
            <UiTooltip :text="i18n.t('help.glossary.seed.definition')" /></span
          ><input
            class="control"
            type="number"
            :value="profile.seed ?? ''"
            @input="emit('update', 'seed', numeric(($event.target as HTMLInputElement).value, 0))"
        /></label>
        <label v-if="profile.type === 'ollama'" class="field"
          ><span
            >{{ i18n.t("providers.think") }}
            <UiTooltip :text="i18n.t('providers.think_help')" /></span
          ><select
            class="control"
            :value="String(profile.think ?? 'false')"
            @change="emit('update', 'think', ($event.target as HTMLSelectElement).value)"
          >
            <option value="false">{{ i18n.t("providers.think_off") }}</option>
            <option value="true">{{ i18n.t("providers.think_on") }}</option>
            <option value="low">{{ i18n.t("providers.think_low") }}</option>
            <option value="medium">{{ i18n.t("providers.think_medium") }}</option>
            <option value="high">{{ i18n.t("providers.think_high") }}</option>
          </select></label
        >
        <label v-if="profile.type === 'ollama'" class="field"
          ><span
            >{{ i18n.t("providers.keep_alive") }}
            <UiTooltip :text="i18n.t('providers.keep_alive_help')" /></span
          ><input
            class="control"
            :value="profile.keep_alive || '10m'"
            @input="emit('update', 'keep_alive', ($event.target as HTMLInputElement).value)"
        /></label>
        <label class="field field-wide"
          ><span
            >{{ i18n.t("providers.extra_options") }}
            <UiTooltip :text="i18n.t('providers.extra_options_help')" /></span
          ><textarea
            class="control provider-json"
            rows="4"
            spellcheck="false"
            :value="String(profile.extra_options || '{}')"
            @input="emit('update', 'extra_options', ($event.target as HTMLTextAreaElement).value)"
          ></textarea>
        </label>
      </div>
    </details>
  </div>
</template>

<style scoped>
.provider-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.provider-fields.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding-top: 12px;
}
.field {
  display: grid;
  align-content: start;
  gap: 6px;
}
.field-wide {
  grid-column: 1 / -1;
}
.field > span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  font-weight: 700;
}
.field small,
.provider-access small {
  color: var(--muted);
  line-height: 1.4;
}
.provider-json {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  font-size: 0.8125rem;
}
.provider-more,
.provider-tools {
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.provider-more summary,
.provider-tools summary {
  cursor: pointer;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 750;
}
@media (max-width: 800px) {
  .provider-fields,
  .provider-fields.three {
    grid-template-columns: 1fr;
  }
  .field-wide,
  .provider-access {
    grid-column: auto;
  }
}
</style>

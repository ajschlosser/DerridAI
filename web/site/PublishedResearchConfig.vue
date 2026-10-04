<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import UiCheckbox from "../src/components/ui/UiCheckbox.vue";
import UiField from "../src/components/ui/UiField.vue";
import UiInput from "../src/components/ui/UiInput.vue";
import UiSelect from "../src/components/ui/UiSelect.vue";
import {
  type PublishedResearchMode,
  type PublishedResearchSettings,
  usePublishedSite,
} from "./siteContext";

const props = withDefaults(
  defineProps<{
    modelValue: PublishedResearchSettings;
    idPrefix?: string;
    disabled?: boolean;
  }>(),
  { idPrefix: "published-research-config", disabled: false },
);
const emit = defineEmits<{
  "update:modelValue": [value: PublishedResearchSettings];
}>();
const site = usePublishedSite();

function update(patch: Partial<PublishedResearchSettings>) {
  emit("update:modelValue", {
    ...props.modelValue,
    ...patch,
    works: patch.works ? [...patch.works] : [...props.modelValue.works],
  });
}

function numberValue(value: string | number | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toggleWork(work: string, checked: boolean) {
  const next = new Set(props.modelValue.works);
  if (checked) next.add(work);
  else next.delete(work);
  update({ works: [...next] });
}
</script>

<template>
  <div class="published-research-config">
    <div class="published-research-config-grid">
      <UiField
        :label="site.t('site.runtime.research_mode')"
        :hint="site.t('site.runtime.research_mode_help')"
        :control-id="`${idPrefix}-mode`"
      >
        <template #default="{ describedby, controlId }">
          <UiSelect
            :id="controlId"
            :model-value="modelValue.mode"
            :aria-describedby="describedby"
            :disabled="disabled"
            @update:model-value="update({ mode: $event as PublishedResearchMode })"
          >
            <option value="auto">{{ site.t("site.runtime.research_mode_auto") }}</option>
            <option value="keyword">{{ site.t("site.runtime.research_mode_keyword") }}</option>
            <option value="semantic">{{ site.t("site.runtime.research_mode_semantic") }}</option>
            <option value="hybrid">{{ site.t("site.runtime.research_mode_hybrid") }}</option>
          </UiSelect>
        </template>
      </UiField>

      <UiField
        :label="site.t('site.runtime.research_k')"
        :hint="site.t('site.runtime.research_k_help')"
        :control-id="`${idPrefix}-k`"
      >
        <template #default="{ describedby, controlId }">
          <UiInput
            :id="controlId"
            type="number"
            :model-value="modelValue.k"
            min="1"
            max="500"
            :aria-describedby="describedby"
            :disabled="disabled"
            @update:model-value="update({ k: numberValue($event, modelValue.k) })"
          />
        </template>
      </UiField>

      <UiField
        :label="site.t('site.runtime.research_fetch_k')"
        :hint="site.t('site.runtime.research_fetch_k_help')"
        :control-id="`${idPrefix}-fetch-k`"
      >
        <template #default="{ describedby, controlId }">
          <UiInput
            :id="controlId"
            type="number"
            :model-value="modelValue.fetchK"
            min="1"
            max="5000"
            :aria-describedby="describedby"
            :disabled="disabled"
            @update:model-value="update({ fetchK: numberValue($event, modelValue.fetchK) })"
          />
        </template>
      </UiField>

      <UiField
        :label="site.t('site.runtime.research_top_n')"
        :hint="site.t('site.runtime.research_top_n_help')"
        :control-id="`${idPrefix}-top-n`"
      >
        <template #default="{ describedby, controlId }">
          <UiInput
            :id="controlId"
            type="number"
            :model-value="modelValue.topN"
            min="1"
            max="100"
            :aria-describedby="describedby"
            :disabled="disabled"
            @update:model-value="update({ topN: numberValue($event, modelValue.topN) })"
          />
        </template>
      </UiField>

      <UiField
        :label="site.t('site.runtime.research_mmr_lambda')"
        :hint="site.t('site.runtime.research_mmr_lambda_help')"
        :control-id="`${idPrefix}-mmr-lambda`"
      >
        <template #default="{ describedby, controlId }">
          <UiInput
            :id="controlId"
            type="number"
            :model-value="modelValue.mmrLambda"
            min="0"
            max="1"
            step="0.01"
            :aria-describedby="describedby"
            :disabled="disabled"
            @update:model-value="
              update({ mmrLambda: numberValue($event, modelValue.mmrLambda) })
            "
          />
        </template>
      </UiField>
    </div>

    <fieldset class="published-work-scope">
      <legend>{{ site.t("site.runtime.research_work_scope") }}</legend>
      <p class="muted">{{ site.t("site.runtime.research_work_scope_help") }}</p>
      <p class="meta" role="status" aria-live="polite">
        {{
          modelValue.works.length
            ? site.t("site.runtime.research_selected_works_count", {
                count: modelValue.works.length,
              })
            : site.t("site.runtime.research_all_works")
        }}
      </p>
      <div class="published-work-options">
        <UiCheckbox
          v-for="item in site.publication.works"
          :key="item.work"
          class="published-work-option"
          :input-id="`${idPrefix}-work-${String(item.work).replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`"
          :label="String(item.work)"
          :model-value="modelValue.works.includes(String(item.work))"
          :disabled="disabled"
          @update:model-value="toggleWork(String(item.work), $event)"
        />
      </div>
    </fieldset>
  </div>
</template>

<style scoped>
.published-research-config {
  display: grid;
  gap: var(--space-5);
}
.published-research-config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
  gap: var(--space-4);
}
.published-work-scope {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
  margin: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}
.published-work-scope legend {
  padding-inline: var(--space-2);
  font-weight: var(--fw-bold);
}
.published-work-scope p {
  margin: 0;
}
.published-work-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
  gap: var(--space-2);
  max-block-size: 16rem;
  overflow: auto;
}
.published-work-option {
  min-width: 0;
}
</style>

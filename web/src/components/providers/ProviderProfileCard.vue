<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed } from "vue";
import type { ProviderProfile } from "../../api/system";
import type { DiscoveredModel } from "../../domain/providerModels";
import { useI18nStore } from "../../stores/i18n";
import ProviderModelPicker from "../ProviderModelPicker.vue";
import ProviderTuningFields from "./ProviderTuningFields.vue";

// One provider profile: a quiet summary row that opens into the essential
// fields. Capacity/advanced settings are one level deeper (ProviderTuningFields).
const props = defineProps<{
  profile: ProviderProfile;
  models: DiscoveredModel[];
  tone: "ready" | "error" | "idle";
  statusText: string;
  isDefault: boolean;
  expanded: boolean;
  busy: string;
  revealed: boolean;
  canRemove: boolean;
  sharedLimit: number;
  sharedEndpoint: boolean;
}>();
const emit = defineEmits<{
  update: [field: string, value: unknown];
  toggle: [];
  "toggle-key": [];
  run: [action: "test" | "warm"];
  "make-default": [];
  remove: [];
}>();
const i18n = useI18nStore();
const modelLabel = computed(() => {
  const { profile } = props;
  if (profile.type === "openai" && profile.model_mode === "auto")
    return i18n.t("providers.mode_auto");
  return String(profile.model || "") || i18n.t("providers.no_model");
});
</script>

<template>
  <li class="provider-card" :class="{ default: isDefault, open: expanded }">
    <div class="provider-row">
      <button
        class="provider-summary"
        type="button"
        :aria-expanded="expanded"
        :aria-controls="`provider-body-${profile.id}`"
        :aria-label="i18n.tf('providers.details_of', { name: profile.name || profile.id })"
        @click="emit('toggle')"
      >
        <span class="provider-dot" :class="tone" aria-hidden="true"></span>
        <span class="provider-identity">
          <span class="provider-title">
            <b>{{ profile.name || profile.id }}</b>
            <span v-if="isDefault" class="status-tag">{{ i18n.t("providers.default") }}</span>
          </span>
          <span class="provider-meta">
            {{
              profile.type === "ollama"
                ? i18n.t("providers.ollama")
                : i18n.t("providers.openai_compatible")
            }}
            · {{ modelLabel }}
          </span>
        </span>
        <span class="provider-status" :class="tone">{{ statusText }}</span>
        <svg class="provider-chevron" viewBox="0 0 16 16" aria-hidden="true">
          <path
            d="M4 6l4 4 4-4"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <button
        class="btn small"
        type="button"
        :disabled="Boolean(busy)"
        @click="emit('run', 'test')"
      >
        {{ busy === "test" ? i18n.t("providers.testing") : i18n.t("providers.test_short") }}
      </button>
    </div>
    <div v-show="expanded" :id="`provider-body-${profile.id}`" class="provider-body">
      <div class="provider-fields">
        <label class="field"
          ><span>{{ i18n.t("providers.profile_name") }}</span
          ><input
            class="control"
            :value="profile.name"
            @input="emit('update', 'name', ($event.target as HTMLInputElement).value)"
        /></label>
        <label class="field"
          ><span>{{ i18n.t("providers.endpoint") }}</span
          ><input
            class="control"
            :value="profile.base_url"
            @input="emit('update', 'base_url', ($event.target as HTMLInputElement).value)"
        /></label>
        <ProviderModelPicker
          :profile-name="profile.name || profile.id"
          :model-value="
            profile.type === 'openai' && profile.model_mode === 'auto'
              ? 'auto'
              : String(profile.model || '')
          "
          :models="models"
          :kind="profile.type === 'openai' ? String(profile.model_kind || 'any') : 'any'"
          :disabled="profile.type === 'openai' && profile.model_mode === 'auto'"
          :busy="busy === 'test'"
          :placeholder="
            profile.type === 'ollama'
              ? i18n.t('providers.model_placeholder_ollama')
              : i18n.t('providers.model_placeholder_openai')
          "
          @update:model-value="emit('update', 'model', $event)"
          @discover="emit('run', 'test')"
        />
        <label v-if="profile.type === 'openai'" class="field"
          ><span>{{ i18n.t("providers.model_mode") }}</span
          ><select
            class="control"
            :value="profile.model_mode || 'auto'"
            @change="emit('update', 'model_mode', ($event.target as HTMLSelectElement).value)"
          >
            <option value="auto">{{ i18n.t("providers.mode_auto") }}</option>
            <option value="discovered">{{ i18n.t("providers.mode_discovered") }}</option>
            <option value="manual">{{ i18n.t("providers.mode_manual") }}</option></select
          ><small>{{ i18n.t("providers.model_mode_help") }}</small></label
        >
        <label v-if="profile.type === 'openai'" class="field"
          ><span>{{ i18n.t("providers.api_key") }}</span
          ><span class="provider-secret-field"
            ><input
              class="control"
              :type="revealed ? 'text' : 'password'"
              autocomplete="off"
              :value="profile.api_key"
              @input="emit('update', 'api_key', ($event.target as HTMLInputElement).value)"
            /><button
              type="button"
              class="btn small provider-secret-toggle"
              :aria-label="
                revealed ? i18n.t('providers.hide_api_key') : i18n.t('providers.show_api_key')
              "
              @click="emit('toggle-key')"
            >
              {{ revealed ? i18n.t("providers.hide") : i18n.t("providers.show") }}
            </button></span
          ></label
        >
        <label class="provider-access"
          ><input
            type="checkbox"
            :checked="Boolean(profile.researcher_enabled)"
            @change="
              emit('update', 'researcher_enabled', ($event.target as HTMLInputElement).checked)
            "
          /><span
            ><b>{{ i18n.t("providers.researcher_access") }}</b
            ><small>{{ i18n.t("providers.researcher_access_help") }}</small></span
          ></label
        >
      </div>
      <ProviderTuningFields
        :profile="profile"
        :shared-limit="sharedLimit"
        :shared-endpoint="sharedEndpoint"
        @update="(f, v) => emit('update', f, v)"
      />
      <footer class="provider-card-footer">
        <button
          class="btn small"
          type="button"
          :disabled="Boolean(busy)"
          @click="emit('run', 'warm')"
        >
          {{ busy === "warm" ? i18n.t("providers.warming") : i18n.t("providers.warm") }}
        </button>
        <button v-if="!isDefault" class="btn small" type="button" @click="emit('make-default')">
          {{ i18n.t("providers.set_default") }}
        </button>
        <button
          class="btn small danger provider-remove"
          type="button"
          :disabled="!canRemove"
          @click="emit('remove')"
        >
          {{ i18n.t("ui.remove") }}
        </button>
      </footer>
    </div>
  </li>
</template>

<style scoped>
.provider-card {
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.provider-card:hover,
.provider-card.open {
  box-shadow: var(--shadow-md, var(--shadow-sm));
}
.provider-card.default {
  border-color: var(--accent);
}
.provider-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 14px;
}
.provider-summary {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 14px 8px 14px 16px;
  border: 0;
  border-radius: var(--radius-card);
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.provider-summary:focus-visible {
  outline: var(--focus-ring-width, 2px) solid var(--focus-ring, var(--accent));
  outline-offset: -2px;
}
.provider-dot {
  flex: none;
  inline-size: 10px;
  block-size: 10px;
  border-radius: 50%;
  background: var(--warning);
}
.provider-dot.ready {
  background: var(--success);
}
.provider-dot.error {
  background: var(--tone-danger-fg);
}
.provider-identity {
  display: grid;
  flex: 1;
  gap: 2px;
  min-width: 0;
}
.provider-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.provider-title b {
  overflow: hidden;
  font-size: 1rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-meta {
  overflow: hidden;
  color: var(--muted);
  font-size: 0.8125rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-status {
  flex: none;
  max-inline-size: 28ch;
  overflow: hidden;
  color: var(--muted);
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-status.ready {
  color: var(--tone-ok-fg);
}
.provider-status.error {
  color: var(--tone-danger-fg);
}
.provider-chevron {
  flex: none;
  inline-size: 16px;
  block-size: 16px;
  color: var(--muted);
  transition: transform 0.15s ease;
}
.open .provider-chevron {
  transform: rotate(180deg);
}
.status-tag {
  flex: none;
  padding: 2px 8px;
  border-radius: var(--radius-pill, 999px);
  background: var(--accent-soft);
  color: var(--accent-fg);
  font-size: 0.75rem;
  font-weight: 800;
}
.provider-body {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-top: 1px solid var(--line);
}
.provider-access {
  grid-column: 1 / -1;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.provider-access input {
  margin-top: 3px;
  accent-color: var(--accent);
}
.provider-access span {
  display: grid;
  gap: 2px;
}
.provider-secret-field {
  display: flex;
  gap: 6px;
  align-items: center;
}
.provider-secret-field .control {
  flex: 1;
  min-width: 0;
}
.provider-secret-toggle {
  flex: 0 0 auto;
  white-space: nowrap;
}
.provider-card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.provider-remove {
  margin-inline-start: auto;
}
.provider-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
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
  font-size: 0.75rem;
  font-weight: 700;
}
.field small,
.provider-access small {
  color: var(--muted);
  line-height: 1.4;
}
@media (max-width: 800px) {
  .provider-status {
    display: none;
  }
  .provider-fields,
  .provider-fields.three {
    grid-template-columns: 1fr;
  }
  .field-wide,
  .provider-access {
    grid-column: auto;
  }
}
@media (prefers-reduced-motion: reduce) {
  .provider-chevron {
    transition: none;
  }
}
</style>

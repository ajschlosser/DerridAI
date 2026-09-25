<script setup lang="ts">
import { computed } from "vue";
import type { ProviderProfile } from "../api/system";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    profiles: ProviderProfile[];
    defaultProfileId?: string;
    label?: string;
    help?: string;
    emptyTitle?: string;
    emptyHelp?: string;
    manageLabel?: string;
    modelNotSetLabel?: string;
    defaultLabel?: string;
    unavailableLabel?: string;
    concurrentLabel?: string;
    contextLabel?: string;
  }>(),
  {
    defaultProfileId: "",
    label: "Provider profile",
    help: "Use a configured LLM provider profile.",
    emptyTitle: "No LLM provider profiles are configured",
    emptyHelp: "Create a provider profile before continuing.",
    manageLabel: "Manage provider profiles",
    modelNotSetLabel: "model not set",
    defaultLabel: "Default",
    unavailableLabel: "Unavailable",
    concurrentLabel: "max concurrent request(s)",
    contextLabel: "context tokens",
  },
);
const emit = defineEmits<{ "update:modelValue": [value: string]; manage: [] }>();
const selectableProfiles = computed(() =>
  props.profiles.filter(
    (profile) => profile.available !== false || profile.id === props.modelValue,
  ),
);
const selected = computed(
  () =>
    props.profiles.find((profile) => profile.id === props.modelValue) ||
    selectableProfiles.value[0] ||
    null,
);
function providerName(profile: ProviderProfile) {
  return profile.type === "ollama" ? "Ollama" : "OpenAI-compatible";
}
function contextWindow(profile: ProviderProfile) {
  const raw = Number(profile.num_ctx || 0);
  return Number.isFinite(raw) && raw > 0 ? raw : 0;
}
</script>

<template>
  <section class="provider-profile-select-component" :aria-label="props.label">
    <div class="provider-picker-head">
      <div>
        <b>{{ props.label }}</b
        ><span>{{ props.help }}</span>
      </div>
      <button type="button" class="provider-manage-button" @click="emit('manage')">
        {{ props.manageLabel }}
      </button>
    </div>

    <template v-if="props.profiles.length">
      <label class="provider-select-field">
        <span class="sr-only">{{ props.label }}</span>
        <select
          class="control provider-select"
          :value="props.modelValue"
          @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="profile in selectableProfiles"
            :key="profile.id"
            :value="profile.id"
            :disabled="profile.available === false"
            :title="profile.availability_error"
          >
            {{ profile.name || profile.id }} · {{ profile.model || props.modelNotSetLabel }}
          </option>
        </select>
      </label>

      <div v-if="selected" class="provider-summary-card">
        <span class="provider-logo" aria-hidden="true">{{
          selected.type === "ollama" ? "O" : "AI"
        }}</span>
        <span class="provider-summary-copy">
          <span class="provider-summary-title"
            ><b>{{ selected.name || selected.id }}</b
            ><span v-if="selected.id === props.defaultProfileId" class="provider-default-chip">{{
              props.defaultLabel
            }}</span></span
          >
          <small
            >{{ providerName(selected) }} · {{ selected.model || props.modelNotSetLabel }}</small
          >
        </span>
        <span class="provider-stat-group">
          <span class="provider-stat"
            ><b>{{ Number(selected.max_concurrent_requests || 1) }}</b
            ><small>{{ props.concurrentLabel }}</small></span
          >
          <span v-if="contextWindow(selected)" class="provider-stat"
            ><b>{{ contextWindow(selected).toLocaleString() }}</b
            ><small>{{ props.contextLabel }}</small></span
          >
        </span>
      </div>
      <p v-if="selected?.available === false" class="provider-unavailable" role="status">
        <b>{{ props.unavailableLabel }}</b>
        <span>{{ selected.availability_error || props.unavailableLabel }}</span>
      </p>
    </template>

    <div v-else class="provider-empty-state">
      <span class="provider-empty-icon" aria-hidden="true">AI</span>
      <span
        ><b>{{ props.emptyTitle }}</b>
        <p>{{ props.emptyHelp }}</p></span
      >
    </div>
  </section>
</template>

<style scoped>
.provider-profile-select-component {
  container-type: inline-size;
  display: grid;
  gap: 11px;
  padding: 14px;
  border: 1px solid var(--line, #e2e8f0);
  border-radius: 12px;
  background: linear-gradient(180deg, var(--card) 0%, var(--card) 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
.provider-picker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.provider-picker-head > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.provider-picker-head b {
  font-size: 0.8125rem;
  color: var(--text, #17233b);
}
.provider-picker-head span {
  max-width: 650px;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted, #64748b);
}
.provider-manage-button {
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 750;
  padding: 3px 0;
  cursor: pointer;
}
.provider-manage-button:hover {
  text-decoration: underline;
}
.provider-manage-button:focus-visible,
.provider-select:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.provider-select-field {
  display: grid;
}
.provider-select {
  width: 100%;
  min-height: 42px;
  font-size: 0.8125rem;
  font-weight: 650;
  background: var(--card);
}
.provider-summary-card {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  gap: 11px;
  align-items: center;
  padding: 10px 11px;
  border: 1px solid color-mix(in srgb, var(--accent, #355f52) 16%, var(--line, #e2e8f0));
  border-radius: 10px;
  background: var(--accent-soft, #eef6f2);
}
.provider-logo {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: #17233b;
  color: var(--accent-on);
  font-size: 0.8125rem;
  font-weight: 850;
  letter-spacing: 0.02em;
}
.provider-summary-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.provider-summary-title {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}
.provider-summary-title b {
  font-size: 0.8125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-summary-copy small {
  font-size: 0.8125rem;
  color: var(--muted, #64748b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-default-chip {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid color-mix(in srgb, var(--accent, #355f52) 25%, var(--line, #e2e8f0));
  font-size: 0.8125rem;
  color: var(--accent-fg);
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.provider-stat-group {
  display: flex;
  align-items: stretch;
  gap: 7px;
}
.provider-stat {
  min-width: 76px;
  display: grid;
  align-content: center;
  gap: 1px;
  padding: 6px 8px;
  border: 1px solid color-mix(in srgb, var(--card) 85%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--card) 68%, transparent);
  text-align: right;
}
.provider-stat b {
  font-size: 0.8125rem;
}
.provider-stat small {
  font-size: 0.8125rem;
  color: var(--muted, #64748b);
  line-height: 1.25;
}
.provider-empty-state {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px dashed var(--line, #d6dee8);
  border-radius: 10px;
  background: var(--soft, #f8fafc);
}
.provider-empty-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--soft);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 850;
}
.provider-empty-state > span:last-child {
  display: grid;
  gap: 3px;
}
.provider-empty-state b {
  font-size: 0.8125rem;
}
.provider-empty-state p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted, #64748b);
}
.provider-unavailable {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--warning-line, #d9a441);
  border-radius: 8px;
  background: var(--warning-soft, #fff8e6);
  color: var(--text, #17233b);
  font-size: 0.8125rem;
  line-height: 1.4;
}
.provider-unavailable span {
  color: var(--muted, #64748b);
  overflow-wrap: anywhere;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
/* The card lives in columns of many widths (a dialog, a settings column), so it stacks by the width
   it is given, not by the viewport. */
@container (max-width:460px) {
  .provider-summary-card {
    grid-template-columns: 40px minmax(0, 1fr);
  }
  .provider-stat-group {
    grid-column: 1/-1;
  }
  .provider-stat {
    flex: 1;
    text-align: left;
  }
}
@media (max-width: 720px) {
  .provider-picker-head {
    align-items: start;
    flex-direction: column;
  }
  .provider-manage-button {
    padding: 0;
  }
}
</style>

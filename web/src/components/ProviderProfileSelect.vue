<script setup lang="ts">
import { computed } from "vue";
import type { ProviderProfile } from "../api/system";

const props = withDefaults(defineProps<{
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
  concurrentLabel?: string;
}>(), {
  defaultProfileId: "",
  label: "Provider profile",
  help: "Use a configured LLM provider profile.",
  emptyTitle: "No LLM provider profiles are configured",
  emptyHelp: "Create a provider profile before continuing.",
  manageLabel: "Manage provider profiles",
  modelNotSetLabel: "model not set",
  defaultLabel: "Default",
  concurrentLabel: "max concurrent request(s)",
});
const emit = defineEmits<{ "update:modelValue": [value: string]; manage: [] }>();
const selected = computed(() => props.profiles.find(profile => profile.id === props.modelValue) || props.profiles[0] || null);
function providerName(profile: ProviderProfile) { return profile.type === "ollama" ? "Ollama" : "OpenAI-compatible"; }
</script>

<template>
  <div class="provider-profile-select-component">
    <template v-if="props.profiles.length">
      <label class="workflow-field workflow-provider-select-field">
        <span>{{ props.label }}</span>
        <select class="control workflow-provider-select" :value="props.modelValue" @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)">
          <option v-for="profile in props.profiles" :key="profile.id" :value="profile.id">
            {{ profile.name || profile.id }} · {{ providerName(profile) }} · {{ profile.model || props.modelNotSetLabel }}{{ profile.id === props.defaultProfileId ? ` · ${props.defaultLabel}` : "" }}
          </option>
        </select>
        <small>{{ props.help }}</small>
      </label>
      <div v-if="selected" class="workflow-provider-summary">
        <span class="workflow-provider-mark">{{ selected.type === "ollama" ? "O" : "AI" }}</span>
        <span><b>{{ selected.name || selected.id }}</b><small>{{ providerName(selected) }} · {{ selected.model || props.modelNotSetLabel }}</small><small>{{ Number(selected.max_concurrent_requests || 1) }} {{ props.concurrentLabel }}</small></span>
        <span v-if="selected.id === props.defaultProfileId" class="provider-default-chip">{{ props.defaultLabel }}</span>
      </div>
    </template>
    <div v-else class="workflow-provider-empty"><b>{{ props.emptyTitle }}</b><p>{{ props.emptyHelp }}</p></div>
    <button type="button" class="btn small" @click="emit('manage')">{{ props.manageLabel }}</button>
  </div>
</template>

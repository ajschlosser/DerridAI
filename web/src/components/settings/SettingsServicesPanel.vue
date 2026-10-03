<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
-->

<script setup lang="ts">
import type {
  ProviderProfile,
  SystemAudioTranscription,
  SystemAudioTranscriptionStatus,
} from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiField from "../ui/UiField.vue";
import UiHealthChip from "../ui/UiHealthChip.vue";
import DocumentNlpLanguagePacks from "./DocumentNlpLanguagePacks.vue";
import SettingsSection from "./SettingsSection.vue";

const props = defineProps<{
  profiles: ProviderProfile[];
  defaultProfileId: string;
  providerStatuses: Record<string, { available?: boolean; checked_at?: string; error?: string }>;
  audio: SystemAudioTranscription | null;
  audioDraft: {
    base_url: string;
    model: string;
    api_key: string;
  };
  audioStatus: SystemAudioTranscriptionStatus | null;
  audioBusy: string;
  audioMessage: string;
}>();
const emit = defineEmits<{
  "update-audio-draft": [value: { base_url: string; model: string; api_key: string }];
  "test-audio": [];
  "save-audio": [];
  "clear-audio-key": [];
  navigate: [path: string, view?: string];
}>();
const i18n = useI18nStore();

function providerReady(profile: ProviderProfile) {
  return Boolean(props.providerStatuses?.[profile.id]?.available);
}
function providerChecked(profile: ProviderProfile) {
  const stamp = props.providerStatuses?.[profile.id]?.checked_at;
  if (!stamp) return i18n.t("settings.not_checked");
  const date = new Date(stamp);
  return Number.isNaN(date.getTime()) ? stamp : date.toLocaleString(i18n.locale);
}
function updateAudio(patch: Partial<{ base_url: string; model: string; api_key: string }>) {
  emit("update-audio-draft", { ...props.audioDraft, ...patch });
}
</script>

<template>
  <div class="settings-services">
    <SettingsSection
      section-id="providers"
      :title="i18n.t('settings.providers_title')"
      :description="i18n.t('settings.providers_help')"
      :persistence="i18n.t('settings.persist.link')"
      status="readonly"
    >
      <ul v-if="profiles.length" class="providers-summary">
        <li v-for="profile in profiles" :key="profile.id">
          <UiHealthChip
            :available="providerReady(profile)"
            :label="String(profile.name || profile.id)"
            :detail="
              providerReady(profile)
                ? i18n.t('settings.provider_ready')
                : i18n.t('settings.provider_not_ready')
            "
          />
          <span>
            {{
              profile.type === "ollama"
                ? i18n.t("settings.provider_ollama")
                : i18n.t("settings.openai_compatible")
            }}
            ·
            {{
              i18n.tf("settings.max_concurrent", {
                count: Number(profile.max_concurrent_requests ?? 1),
              })
            }}
            · {{ profile.model || i18n.t("language.model_not_set") }}
          </span>
          <small>{{ i18n.tf("settings.last_checked", { time: providerChecked(profile) }) }}</small>
          <b v-if="profile.id === defaultProfileId">{{ i18n.t("ui.default") }}</b>
        </li>
      </ul>
      <p v-else class="note">{{ i18n.t("settings.no_providers") }}</p>
      <template #actions>
        <UiButton
          variant="primary"
          icon="spark"
          :label="i18n.t('settings.open_providers')"
          @click="emit('navigate', '/providers', 'providers')"
        />
      </template>
    </SettingsSection>

    <SettingsSection
      section-id="audio"
      :title="i18n.t('settings.audio_title')"
      :description="i18n.t('settings.audio_help')"
      :persistence="i18n.t('settings.persist.backend')"
    >
      <div class="config-grid">
        <UiField :label="i18n.t('settings.audio_base_url')">
          <input
            id="settings-field-audio-base-url"
            class="control"
            type="url"
            :value="audioDraft.base_url"
            @input="updateAudio({ base_url: ($event.target as HTMLInputElement).value })"
          />
        </UiField>
        <UiField :label="i18n.t('settings.audio_model')">
          <input
            id="settings-field-audio-model"
            class="control"
            :value="audioDraft.model"
            @input="updateAudio({ model: ($event.target as HTMLInputElement).value })"
          />
        </UiField>
        <UiField
          wide
          :label="i18n.t('settings.audio_key')"
          :hint="
            audio?.has_key
              ? i18n.t(
                  audio.key_source === 'settings'
                    ? 'settings.audio_key_stored'
                    : 'settings.audio_key_from_environment',
                )
              : i18n.t('settings.audio_key_missing')
          "
        >
          <input
            id="settings-field-audio-key"
            class="control"
            type="password"
            autocomplete="off"
            :value="audioDraft.api_key"
            :placeholder="i18n.t('settings.audio_key_placeholder')"
            @input="updateAudio({ api_key: ($event.target as HTMLInputElement).value })"
          />
        </UiField>
      </div>
      <p
        v-if="audioStatus"
        class="embedding-probe"
        :data-state="audioStatus.reachable ? 'ok' : 'failed'"
        role="status"
      >
        <strong>
          {{
            i18n.t(
              audioStatus.reachable ? "settings.audio_reachable" : "settings.audio_unreachable",
            )
          }}
        </strong>
        <span v-if="audioStatus.error">{{ audioStatus.error }}</span>
        <span v-if="audioStatus.hint">{{ audioStatus.hint }}</span>
      </p>
      <p v-if="audioMessage" class="note" role="status">{{ audioMessage }}</p>
      <template #actions>
        <UiButton
          :disabled="audioBusy !== ''"
          :label="i18n.t('settings.audio_test')"
          @click="emit('test-audio')"
        />
        <UiButton
          v-if="audio?.key_source === 'settings'"
          :disabled="audioBusy !== ''"
          :label="i18n.t('settings.audio_clear_key')"
          @click="emit('clear-audio-key')"
        />
        <UiButton
          variant="primary"
          :disabled="audioBusy !== ''"
          :label="i18n.t('settings.audio_save')"
          @click="emit('save-audio')"
        />
      </template>
    </SettingsSection>

    <SettingsSection
      section-id="language-packs"
      :title="i18n.t('settings.nlp_packs_title')"
      :description="i18n.t('settings.nlp_packs_help')"
      :persistence="i18n.t('settings.persist.backend')"
    >
      <DocumentNlpLanguagePacks />
    </SettingsSection>
  </div>
</template>

<style scoped>
.settings-services {
  display: grid;
  gap: 18px;
}
.providers-summary {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.providers-summary li {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel-2);
}
.providers-summary span,
.providers-summary small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.embedding-probe {
  display: grid;
  gap: 4px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.embedding-probe[data-state="ok"] {
  border-color: var(--tone-ok-fg, var(--line));
}
.embedding-probe[data-state="failed"] {
  border-color: var(--tone-warn-fg, var(--line));
}
</style>

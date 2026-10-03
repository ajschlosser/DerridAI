<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
-->

<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiField from "../ui/UiField.vue";
import SettingsSection from "./SettingsSection.vue";

defineProps<{
  modelValue: string;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: string];
  "reset-columns": [];
  "expand-panels": [];
  "expand-sidebar": [];
  "restore-upsert": [];
  "clear-updates": [];
  "open-nuke": [];
  navigate: [path: string];
}>();
const i18n = useI18nStore();
</script>

<template>
  <div class="settings-troubleshooting">
    <SettingsSection
      section-id="viewer"
      :title="i18n.t('settings.viewer_title')"
      :description="i18n.t('settings.viewer_help')"
      :persistence="i18n.t('settings.persist.browser')"
    >
      <p class="note">{{ i18n.t("settings.viewer_recovery_help") }}</p>
      <template #actions>
        <UiButton :label="i18n.t('settings.reset_columns')" @click="emit('reset-columns')" />
        <UiButton :label="i18n.t('settings.expand_panels')" @click="emit('expand-panels')" />
        <UiButton :label="i18n.t('settings.expand_sidebar')" @click="emit('expand-sidebar')" />
        <UiButton :label="i18n.t('settings.restore_upsert')" @click="emit('restore-upsert')" />
        <UiButton
          variant="danger"
          icon="history"
          :label="i18n.t('settings.clear_updates')"
          @click="emit('clear-updates')"
        />
        <UiButton
          icon="dashboard"
          :label="i18n.t('nav.home')"
          @click="emit('navigate', '/')"
        />
      </template>
    </SettingsSection>

    <SettingsSection
      class="settings-danger-zone"
      section-id="nuke"
      :title="i18n.t('config.nuke.title')"
      :description="i18n.t('config.nuke.help')"
      :persistence="i18n.t('settings.persist.backend')"
      status="readonly"
    >
      <p class="settings-danger-summary">{{ i18n.t("config.nuke.scope_help") }}</p>
      <p class="info error">{{ i18n.t("config.nuke.irreversible") }}</p>
      <UiField
        :label="i18n.t('config.nuke.type_to_enable')"
        :hint="i18n.t('config.nuke.type_to_enable_help')"
      >
        <input
          id="settings-field-nuke"
          class="control"
          :value="modelValue"
          autocomplete="off"
          @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        />
      </UiField>
      <template #actions>
        <UiButton
          variant="danger"
          :label="i18n.t('config.nuke.button')"
          :disabled="modelValue !== 'NUKE'"
          :disabled-reason="i18n.t('config.nuke.type_to_enable_help')"
          @click="emit('open-nuke')"
        />
      </template>
    </SettingsSection>
  </div>
</template>

<style scoped>
.settings-troubleshooting {
  display: grid;
  gap: 18px;
}
.settings-danger-zone {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid var(--danger);
  border-radius: 12px;
  background: var(--panel-2);
}
.settings-danger-summary {
  margin: 0;
  max-width: 68ch;
  color: var(--muted);
  line-height: 1.5;
}
</style>

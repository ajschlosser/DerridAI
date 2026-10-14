<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
-->

<script setup lang="ts">
import { ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import DataRetentionSettings from "./DataRetentionSettings.vue";
import SettingsSection from "./SettingsSection.vue";

defineProps<{
  backupCounts: {
    files: number;
    jobs: number;
  };
}>();
const emit = defineEmits<{
  backup: [];
  "restore-file": [file: File];
  navigate: [path: string, view?: string];
}>();
const i18n = useI18nStore();
const restoreInput = ref<HTMLInputElement | null>(null);

function chooseRestore() {
  restoreInput.value?.click();
}
function onRestoreFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] || null;
  input.value = "";
  if (file) emit("restore-file", file);
}
</script>

<template>
  <div class="settings-data">
    <SettingsSection
      section-id="data-workspaces"
      :title="i18n.t('settings.data_workspaces_title')"
      :description="i18n.t('settings.data_workspaces_help')"
      :persistence="i18n.t('settings.persist.link')"
    >
      <template #actions>
        <UiButton
          icon="database"
          :label="i18n.t('runtime.system_data')"
          @click="emit('navigate', '/system-data')"
        />
        <UiButton
          icon="database"
          :label="i18n.t('nav.vector')"
          @click="emit('navigate', '/databases', 'vector')"
        />
      </template>
    </SettingsSection>

    <SettingsSection
      section-id="data-retention"
      :title="i18n.t('settings.retention_title')"
      :description="i18n.t('settings.retention_help')"
      :persistence="i18n.t('settings.persist.backend')"
    >
      <DataRetentionSettings />
    </SettingsSection>

    <SettingsSection
      section-id="backup"
      :title="i18n.t('settings.backup')"
      :description="i18n.t('settings.backup_help')"
      :persistence="i18n.t('settings.persist.browser')"
    >
      <p class="info warn">{{ i18n.t("settings.backup_keys_warning") }}</p>
      <p class="backup-summary">
        <span>
          <b>{{ backupCounts.files.toLocaleString(i18n.locale) }}</b>
          {{ i18n.t("settings.jsonl_tabs") }}
        </span>
        <span>
          <b>{{ backupCounts.jobs.toLocaleString(i18n.locale) }}</b>
          {{ i18n.t("settings.active_jobs") }}
        </span>
      </p>
      <input
        ref="restoreInput"
        type="file"
        accept=".zip,application/zip"
        hidden
        @change="onRestoreFile"
      />
      <template #actions>
        <UiButton
          variant="primary"
          icon="download"
          :label="i18n.t('settings.download_backup')"
          @click="emit('backup')"
        />
        <UiButton icon="upload" :label="i18n.t('settings.restore_backup')" @click="chooseRestore" />
      </template>
    </SettingsSection>
  </div>
</template>

<style scoped>
.settings-data {
  display: grid;
  gap: 18px;
}
.backup-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0;
  color: var(--muted);
}
</style>

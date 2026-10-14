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
import SettingsSection from "./SettingsSection.vue";

const emit = defineEmits<{
  navigate: [path: string];
}>();
const i18n = useI18nStore();
</script>

<template>
  <SettingsSection
    section-id="security"
    :title="i18n.t('settings.security_title')"
    :description="i18n.t('settings.security_help')"
    :persistence="i18n.t('settings.persist.link')"
    status="readonly"
  >
    <p class="note">{{ i18n.t("roles.users_link_help") }}</p>
    <template #actions>
      <UiButton icon="users" :label="i18n.t('nav.users')" @click="emit('navigate', '/users')" />
      <UiButton icon="roles" :label="i18n.t('nav.roles')" @click="emit('navigate', '/roles')" />
    </template>
  </SettingsSection>
</template>

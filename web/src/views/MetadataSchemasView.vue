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
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { ProviderProfile } from "../api/system";
import MetadataSchemaEditor from "../components/MetadataSchemaEditor.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import { useI18nStore } from "../stores/i18n";
import {
  getProviderProfilesForUi,
  getDefaultProviderProfileId,
} from "../domain/sharedProviderProfiles";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const profiles = ref<ProviderProfile[]>([]);
const defaultId = ref("");

function refreshProviders() {
  profiles.value = (getProviderProfilesForUi() || []) as ProviderProfile[];
  defaultId.value = String(getDefaultProviderProfileId() || "");
}

const previewProfiles = computed(() => profiles.value);
const selectedSchemaId = computed(() => String(route.query.schema || "default"));
const selectedSchemaTab = computed(() => String(route.query.tab || "fields"));

function setSchemaRoute(id: string) {
  void router.replace({
    name: "schemas",
    query: {
      ...route.query,
      schema: id && id !== "default" ? id : undefined,
    },
  });
}

function setSchemaTabRoute(tab: string) {
  void router.replace({
    name: "schemas",
    query: {
      ...route.query,
      tab: tab && tab !== "fields" ? tab : undefined,
    },
  });
}

onMounted(() => refreshProviders());
</script>

<template>
  <main class="vue-native-page schemas-page" aria-labelledby="schemas-page-title">
    <UiPageHeader
      :kicker="i18n.t('section.corpus_management')"
      :title="i18n.t('schemas.manage_title')"
      title-id="schemas-page-title"
      :description="i18n.t('schemas.manage_help')"
    />
    <MetadataSchemaEditor
      :provider-profiles="previewProfiles"
      :default-provider-id="defaultId"
      :initial-schema-id="selectedSchemaId"
      :initial-tab="selectedSchemaTab"
      @selection="setSchemaRoute"
      @tab="setSchemaTabRoute"
    />
  </main>
</template>

<style scoped>
.schemas-page {
  display: grid;
  gap: var(--page-gap, 12px);
  align-content: start;
}
</style>

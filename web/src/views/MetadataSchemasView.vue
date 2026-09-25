<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { ProviderProfile } from "../api/system";
import MetadataSchemaEditor from "../components/MetadataSchemaEditor.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../runtime/runtime.js";

const i18n = useI18nStore();
const profiles = ref<ProviderProfile[]>([]);
const defaultId = ref("");

function refreshProviders() {
  profiles.value = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
  defaultId.value = String(runtime.getDefaultProviderProfileId?.() || "");
}

const previewProfiles = computed(() => profiles.value);

onMounted(() => refreshProviders());
</script>

<template>
  <main class="vue-native-page schemas-page" aria-labelledby="schemas-page-title">
    <UiPageHeader
      :kicker="i18n.t('section.system')"
      :title="i18n.t('schemas.manage_title')"
      title-id="schemas-page-title"
      :description="i18n.t('schemas.manage_help')"
    />
    <MetadataSchemaEditor :provider-profiles="previewProfiles" :default-provider-id="defaultId" />
  </main>
</template>

<style scoped>
.schemas-page {
  display: grid;
  gap: var(--page-gap, 12px);
  align-content: start;
}
</style>

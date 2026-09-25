<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref } from "vue";
import AppIcon from "./AppIcon.vue";
import UiPageHeader from "./ui/UiPageHeader.vue";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(
  defineProps<{
    languageCount?: number;
    keyCount?: number;
    policyPendingCount?: number;
    title?: string;
    description?: string;
  }>(),
  { languageCount: 0, keyCount: 0, policyPendingCount: 0, title: "", description: "" },
);
const emit = defineEmits<{ install: [] }>();
const i18n = useI18nStore();
const installButton = ref<HTMLButtonElement | null>(null);
defineExpose({ focusInstall: () => installButton.value?.focus() });
</script>

<template>
  <UiPageHeader
    class="language-workspace-header"
    :kicker="`${i18n.t('section.system')} · ${i18n.t('language.workspace_kicker')}`"
    :title="props.title || i18n.t('language.page_title')"
    title-id="language-page-title"
    :description="props.description || i18n.t('language.page_description_modern')"
    :actions-label="i18n.t('language.page_actions')"
  >
    <template #actions>
      <div class="language-workspace-stats" :aria-label="i18n.t('language.localization_summary')">
        <span
          ><b>{{ props.languageCount }}</b
          >{{ i18n.t("language.locales") }}</span
        >
        <span
          ><b>{{ props.keyCount.toLocaleString(i18n.locale) }}</b
          >{{ i18n.t("language.source_strings") }}</span
        >
        <span v-if="props.policyPendingCount"
          ><b>{{ props.policyPendingCount }}</b
          >{{ i18n.t("language.content_policy_needed") }}</span
        >
      </div>
      <button ref="installButton" type="button" class="btn primary" @click="emit('install')">
        <AppIcon name="plus" />{{ i18n.t("language.install") }}
      </button>
    </template>
  </UiPageHeader>
</template>

<style scoped>
.language-workspace-stats {
  display: flex;
  gap: var(--space-2);
}
.language-workspace-stats span {
  min-width: 82px;
  display: grid;
  gap: 1px;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.language-workspace-stats b {
  font-size: var(--fs-md);
  color: var(--text-secondary);
  letter-spacing: 0;
}
.language-workspace-header :deep(.btn svg) {
  width: 16px;
  height: 16px;
}
@media (max-width: 560px) {
  .language-workspace-stats {
    display: none;
  }
}
</style>

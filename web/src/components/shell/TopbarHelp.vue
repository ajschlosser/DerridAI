<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    open: boolean;
    showTrigger?: boolean;
    canFaq?: boolean;
    canSettings?: boolean;
  }>(),
  { showTrigger: true, canFaq: false, canSettings: true },
);
const emit = defineEmits<{ "update:open": [value: boolean]; navigate: [view: string] }>();
const i18n = useI18nStore();

function openHelp() {
  emit("update:open", true);
}
function closeHelp() {
  emit("update:open", false);
}
function go(view: string) {
  closeHelp();
  emit("navigate", view);
}
</script>
<template>
  <UiButton
    v-if="showTrigger"
    variant="ghost"
    icon="help"
    icon-only
    :label="i18n.t('ui.help', 'Help')"
    @click="openHelp"
  />
  <UiDialog
    :open="props.open"
    size="medium"
    :title="i18n.t('ui.help_title', 'Using DerridAI')"
    :description="i18n.t('ui.help_body', 'Search the corpus from the bar at the top. The sidebar opens workspaces. Your account menu has settings and sign out. Interface language sits next to it.')"
    :close-label="i18n.t('common.close', 'Close')"
    @close="closeHelp"
  >
    <p>{{ i18n.t("ui.help_search", "Command search focuses with Ctrl K (⌘K on Apple platforms).") }}</p>
    <p>{{ i18n.t("ui.help_compact", "On a narrow screen, language and help move into the account menu.") }}</p>
    <template #footer>
      <div class="help-footer-actions">
        <UiButton
          v-if="canSettings"
          :label="i18n.t('ui.help_settings', 'Open Settings')"
          icon="gear"
          @click="go('config')"
        />
        <UiButton
          v-if="canFaq"
          :label="i18n.t('ui.help_response_library', 'Open Response Library')"
          icon="spark"
          @click="go('faq')"
        />
        <UiButton variant="primary" :label="i18n.t('common.close', 'Close')" @click="closeHelp" />
      </div>
    </template>
  </UiDialog>
</template>
<style scoped>
p {
  margin: 0 0 12px;
  max-width: 70ch;
  color: var(--text-2, var(--text));
  font-size: 0.875rem;
  line-height: 1.5;
}
.help-footer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  margin-inline-start: auto;
}
</style>

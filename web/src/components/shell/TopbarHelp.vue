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
    :label="i18n.t('ui.help')"
    @click="openHelp"
  />
  <UiDialog
    :open="props.open"
    size="medium"
    :title="i18n.t('ui.help_title')"
    :description="i18n.t('ui.help_body')"
    :close-label="i18n.t('common.close')"
    @close="closeHelp"
  >
    <p>{{ i18n.t("ui.help_search") }}</p>
    <p>{{ i18n.t("ui.help_compact") }}</p>
    <template #footer>
      <div class="help-footer-actions">
        <UiButton
          variant="primary"
          :label="i18n.t('help.open_center')"
          icon="help"
          @click="go('help')"
        />
        <UiButton
          v-if="canSettings"
          :label="i18n.t('ui.help_settings')"
          icon="gear"
          @click="go('config')"
        />
        <UiButton
          v-if="canFaq"
          :label="i18n.t('ui.help_response_library')"
          icon="spark"
          @click="go('faq')"
        />
        <UiButton variant="primary" :label="i18n.t('common.close')" @click="closeHelp" />
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

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
import { ref, onMounted, nextTick, type ComponentPublicInstance } from "vue";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchThread } from "../../types/researchThreads";

const props = defineProps<{
  thread: ResearchThread;
  action: "rename" | "delete";
  busy: boolean;
  error: string;
}>();
const emit = defineEmits<{ close: []; save: [title: string]; remove: [] }>();
const i18n = useI18nStore();
const title = ref(props.thread.title);
const form = ref<HTMLFormElement | null>(null);
const titleInput = ref<HTMLInputElement | null>(null);
const cancelButton = ref<ComponentPublicInstance | null>(null);
onMounted(async () => {
  await nextTick();
  // Focus content rather than the shared close-button tooltip; Escape then closes in one press.
  if (props.action === "rename") titleInput.value?.focus();
  else
    (cancelButton.value?.$el as HTMLElement | undefined)
      ?.querySelector<HTMLButtonElement>("button")
      ?.focus();
});
</script>
<template>
  <UiDialog
    :title="i18n.t(action === 'rename' ? 'research.thread_rename' : 'research.thread_delete')"
    :description="action === 'delete' ? i18n.t('research.thread_delete_help') : ''"
    :close-label="i18n.t('ui.cancel')"
    :dismissible="!busy"
    size="medium"
    @close="emit('close')"
  >
    <form
      v-if="action === 'rename'"
      id="research-thread-rename"
      ref="form"
      @submit.prevent="emit('save', title.trim())"
    >
      <label for="research-thread-title">{{ i18n.t("research.thread_title") }}</label>
      <input
        id="research-thread-title"
        ref="titleInput"
        v-model="title"
        class="input"
        maxlength="200"
        required
        :disabled="busy"
      />
    </form>
    <p v-else>{{ thread.title }}</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="busy" role="status">{{ i18n.t("loading.updating") }}</p>
    <template #footer>
      <UiButton
        ref="cancelButton"
        button-class="thread-dialog-cancel"
        :label="i18n.t('ui.cancel')"
        :disabled="busy"
        @click="emit('close')"
      />
      <UiButton
        v-if="action === 'rename'"
        button-class="thread-title-save"
        :label="i18n.t('ui.save')"
        :disabled="busy || !title.trim()"
        @click="form?.requestSubmit()"
      />
      <UiButton
        v-else
        :label="i18n.t('research.thread_delete')"
        variant="danger"
        :disabled="busy"
        @click="emit('remove')"
      />
    </template>
  </UiDialog>
</template>
<style scoped>
input {
  color: var(--text-primary);
  background: var(--surface-inset);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  font-size: var(--fs-base);
  min-height: var(--control-height);
  display: block;
  width: 100%;
  margin-block-start: calc(var(--page-gap) / 2);
}
</style>

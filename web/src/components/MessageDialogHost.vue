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
import { computed, nextTick, ref, watch } from "vue";
import { useMessageDialog } from "../composables/messageDialog";
import { useI18nStore } from "../stores/i18n";

const { queue, settle } = useMessageDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const current = computed(() => queue.value[0] ?? null);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  () => current.value?.id,
  async (id) => {
    await nextTick();
    const dialog = dialogRef.value;
    if (!dialog) return;
    if (id === undefined) {
      if (dialog.open) dialog.close();
    } else if (!dialog.open) {
      dialog.showModal();
    }
  },
  { immediate: true },
);

function finish(confirmed: boolean) {
  const request = current.value;
  if (!request) return;
  dialogRef.value?.close();
  settle(request.id, confirmed);
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="message-dialog"
    :class="current?.tone ?? 'info'"
    role="alertdialog"
    aria-labelledby="message-dialog-title"
    aria-describedby="message-dialog-body"
    @cancel.prevent="finish(false)"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="message-dialog-title" class="dialog-title">
            {{ current.title ?? i18n.t("ui.notice") }}
          </h2>
          <div v-if="current.detail" class="dialog-subtitle">{{ current.detail }}</div>
        </div>
        <button
          class="btn icon-only"
          type="button"
          :aria-label="i18n.t('ui.close')"
          @click="finish(false)"
        >
          ×
        </button>
      </div>
      <div class="db">
        <div id="message-dialog-body" class="message-modal-body">{{ current.message }}</div>
      </div>
      <div class="da">
        <button v-if="current.cancelLabel" class="btn" type="button" @click="finish(false)">
          {{ current.cancelLabel }}
        </button>
        <button
          class="btn"
          :class="current.tone === 'danger' ? 'danger' : 'primary'"
          type="button"
          autofocus
          @click="finish(true)"
        >
          {{ current.confirmLabel ?? i18n.t("ui.ok") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

<style scoped>
/* Preserve line breaks in the message, as the legacy dialog did. */
.message-modal-body {
  white-space: pre-line;
  overflow-wrap: anywhere;
}
</style>

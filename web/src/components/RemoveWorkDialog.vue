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
import { nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { useRemoveWorkDialog } from "../composables/removeWorkDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useRemoveWorkDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const selectedIds = ref<string[]>([]);
const removeDb = ref(false);
const busy = ref(false);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    selectedIds.value = request ? request.files.map((file) => file.id) : [];
    removeDb.value = false;
    busy.value = false;
    await nextTick();
    const dialog = dialogRef.value;
    if (!dialog) return;
    if (!request) {
      if (dialog.open) dialog.close();
    } else if (!dialog.open) {
      dialog.showModal();
    }
  },
  { immediate: true },
);

async function confirm() {
  const request = current.value;
  if (!request || busy.value) return;
  const useDb = Boolean(removeDb.value && request.dbStore);
  if (!selectedIds.value.length && !useDb) {
    toast(i18n.t("works.select_file_or_chroma"), { tone: "warning" });
    return;
  }
  busy.value = true;
  try {
    await request.confirm({ fileIds: [...selectedIds.value], removeDb: useDb });
    close();
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: i18n.t("works.remove_failed"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="message-dialog danger remove-work-dialog"
    aria-labelledby="removeWorkTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="removeWorkTitle" class="dialog-title">{{ i18n.t("works.remove_entire") }}</h2>
          <div class="dialog-subtitle">
            {{ current.work }} · {{ i18n.t("works.destructive_operation") }}
          </div>
        </div>
        <button
          class="btn icon-only"
          type="button"
          :aria-label="i18n.t('ui.close')"
          @click="close()"
        >
          ×
        </button>
      </div>
      <div class="db remove-work-body">
        <div class="info warn">{{ i18n.t("works.remove_help") }}</div>
        <div class="remove-work-files">
          <label v-for="file in current.files" :key="file.id" class="check-item">
            <input v-model="selectedIds" type="checkbox" :value="file.id" />
            <span>
              <b>{{ file.name }}</b>
              <small>{{
                i18n.tf("works.matching_records", { count: file.count.toLocaleString() })
              }}</small>
            </span>
          </label>
        </div>
        <label class="check-item">
          <input
            v-model="removeDb"
            type="checkbox"
            :disabled="!current.dbStore"
            :title="current.dbStore ? undefined : i18n.t('works.select_or_create_db')"
          />
          <span>
            <b>{{ i18n.t("works.also_remove_chroma") }}</b>
            <small>{{ current.dbStore || i18n.t("works.select_collection") }}</small>
          </span>
        </label>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.cancel") }}</button>
        <button class="btn danger" type="button" :disabled="busy" @click="confirm()">
          {{ busy ? i18n.t("works.removing") : i18n.t("works.remove_work") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

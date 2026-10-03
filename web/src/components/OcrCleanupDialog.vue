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
import { useOcrCleanupDialog, type OcrCleanupScope } from "../composables/ocrCleanupDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useOcrCleanupDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
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

async function choose(scope: OcrCleanupScope) {
  const request = current.value;
  if (!request) return;
  close();
  try {
    await request.choose(scope);
  } catch (error) {
    void openMessageDialog({
      title: i18n.t("ui.clean_ocr"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    aria-labelledby="ocrCleanupTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="ocrCleanupTitle" class="dialog-title">{{ i18n.t("ui.clean_ocr") }}</h2>
          <div class="dialog-subtitle">{{ i18n.t("records.ocr.subtitle") }}</div>
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
      <div class="db ocr-clean-options">
        <button
          class="scope-card"
          type="button"
          :disabled="!current.active"
          @click="choose('active')"
        >
          <b>{{ i18n.t("records.ocr.active_tab") }}</b>
          <span>{{
            current.active
              ? i18n.tf("records.ocr.active_meta", {
                  count: current.active.recordCount.toLocaleString(),
                  name: current.active.name,
                })
              : i18n.t("records.ocr.no_tab")
          }}</span>
        </button>
        <button
          class="scope-card"
          type="button"
          :disabled="!current.selectedCount"
          @click="choose('selected')"
        >
          <b>{{ i18n.t("records.ocr.selected") }}</b>
          <span>{{
            i18n.tf("records.ocr.selected_meta", { count: current.selectedCount.toLocaleString() })
          }}</span>
        </button>
        <button class="scope-card" type="button" @click="choose('review')">
          <b>{{ i18n.t("records.ocr.review") }}</b>
          <span>{{
            i18n.tf("records.ocr.review_meta", { count: current.reviewCount.toLocaleString() })
          }}</span>
        </button>
        <button class="scope-card" type="button" @click="choose('all')">
          <b>{{ i18n.t("records.ocr.all") }}</b>
          <span>{{
            i18n.tf("records.ocr.all_meta", {
              count: current.allCount.toLocaleString(),
              tabs: current.fileCount,
            })
          }}</span>
        </button>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.cancel") }}</button>
      </div>
    </template>
  </dialog>
</template>

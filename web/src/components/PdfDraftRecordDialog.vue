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
import { usePdfDraftRecordDialog } from "../composables/pdfDraftRecordDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = usePdfDraftRecordDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const json = ref("");
const fileId = ref("");
const storeName = ref("");
const saving = ref(false);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    if (request) {
      json.value = request.recordJson;
      fileId.value = "";
      storeName.value = "";
      saving.value = false;
    }
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

async function save() {
  const request = current.value;
  if (!request || saving.value) return;
  saving.value = true;
  try {
    const done = await request.save({
      json: json.value,
      fileId: fileId.value,
      storeName: storeName.value,
    });
    if (done && current.value === request) close();
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="pdf-draft-dialog"
    aria-labelledby="pdfDraftTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="pdfDraftTitle" class="dialog-title">{{ i18n.t("jobs.draft.title") }}</h2>
          <div class="dialog-subtitle">
            {{ current.title }} · {{ i18n.tf("jobs.draft.subtitle", { page: current.page }) }}
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
      <div class="db pdf-draft-body">
        <div class="info warn">{{ i18n.t("jobs.draft.warn") }}</div>
        <textarea
          v-model="json"
          class="pdf-draft-json"
          spellcheck="false"
          :aria-label="i18n.t('jobs.draft.title')"
        ></textarea>
        <div class="pdf-draft-targets">
          <div class="field">
            <label for="pdfDraftFile">{{ i18n.t("jobs.draft.jsonl") }}</label>
            <select id="pdfDraftFile" v-model="fileId" class="control">
              <option value="">{{ i18n.t("jobs.draft.no_jsonl") }}</option>
              <option v-for="file in current.files" :key="file.id" :value="file.id">
                {{ file.name }} · {{ i18n.tf("jobs.draft.file_records", { count: file.count }) }}
              </option>
            </select>
          </div>
          <div class="field">
            <label for="pdfDraftStore">{{ i18n.t("jobs.draft.chroma") }}</label>
            <select
              id="pdfDraftStore"
              v-model="storeName"
              class="control"
              :disabled="!current.stores.length"
              :title="current.stores.length ? undefined : i18n.t('jobs.draft.chroma_required')"
            >
              <option value="">
                {{
                  current.stores.length
                    ? i18n.t("jobs.draft.no_chroma")
                    : i18n.t("jobs.draft.no_db")
                }}
              </option>
              <option v-for="store in current.stores" :key="store.id" :value="store.id">
                {{ store.name }} ·
                {{ i18n.tf("jobs.draft.file_records", { count: store.count.toLocaleString() }) }}
              </option>
            </select>
          </div>
        </div>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.cancel") }}</button>
        <button class="btn primary" type="button" :disabled="saving" @click="save()">
          {{ i18n.t("jobs.draft.add") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

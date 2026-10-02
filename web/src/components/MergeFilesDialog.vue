<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { useMergeFilesDialog } from "../composables/mergeFilesDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useMergeFilesDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const picked = ref<string[]>([]);
const name = ref("");
const download = ref(false);
const busy = ref(false);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    picked.value = (request?.files ?? []).map((file) => file.id);
    name.value = request?.defaultName ?? "";
    download.value = false;
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

async function merge() {
  const request = current.value;
  if (!request || busy.value) return;
  busy.value = true;
  try {
    const ok = await request.merge({
      fileIds: picked.value,
      name: name.value,
      download: download.value,
    });
    if (ok) close();
    else busy.value = false;
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: i18n.t("records.merge.title"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="merge-dialog"
    aria-labelledby="mergeFilesTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="mergeFilesTitle" class="dialog-title">{{ i18n.t("records.merge.title") }}</h2>
          <div class="dialog-subtitle">{{ i18n.t("records.merge.subtitle") }}</div>
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
      <div class="db">
        <div class="merge-actions">
          <button
            class="btn small"
            type="button"
            @click="picked = current.files.map((file) => file.id)"
          >
            {{ i18n.t("ui.select_all") }}
          </button>
          <button class="btn small" type="button" @click="picked = []">
            {{ i18n.t("ui.clear") }}
          </button>
        </div>
        <div class="merge-file-list">
          <label v-for="file in current.files" :key="file.id" class="merge-file-item">
            <input v-model="picked" type="checkbox" :value="file.id" />
            <span>
              <b>{{ file.name }}</b>
              <small>{{
                i18n.tf("records.merge.file_records", { count: file.recordCount.toLocaleString() })
              }}</small>
            </span>
          </label>
        </div>
        <div class="field">
          <label for="mergeFilesName">{{ i18n.t("records.merge.filename") }}</label>
          <input id="mergeFilesName" v-model="name" class="control" />
        </div>
        <label class="check-item">
          <input v-model="download" type="checkbox" />
          <span>{{ i18n.t("records.merge.download") }}</span>
        </label>
        <div class="info">{{ i18n.t("records.merge.help") }}</div>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.cancel") }}</button>
        <button class="btn primary" type="button" :disabled="busy" @click="merge()">
          {{ i18n.t("records.merge.create") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

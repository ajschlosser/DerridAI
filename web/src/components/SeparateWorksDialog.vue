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
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { useSeparateWorksDialog } from "../composables/separateWorksDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useSeparateWorksDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const sourceId = ref("");
const selected = ref<string[]>([]);
const removeFromSource = ref(false);
const busy = ref(false);

const source = computed(
  () => current.value?.sources.find((item) => item.id === sourceId.value) ?? null,
);

function resetSelection() {
  selected.value = (source.value?.groups ?? [])
    .filter((group) => group.defaultChecked)
    .map((group) => group.work);
}

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    sourceId.value = request?.sources[0]?.id ?? "";
    resetSelection();
    removeFromSource.value = false;
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
watch(sourceId, resetSelection);

async function create() {
  const request = current.value;
  if (!request || busy.value) return;
  if (!selected.value.length) {
    toast(i18n.t("works.select_at_least_one"), { tone: "warning" });
    return;
  }
  busy.value = true;
  try {
    await request.confirm({
      fileId: sourceId.value,
      works: [...selected.value],
      removeFromSource: removeFromSource.value,
    });
    close();
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: i18n.t("works.separate_works_title"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="work-separate-dialog"
    aria-labelledby="separateWorksTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <span class="section-label">{{ i18n.t("works.jsonl_organization") }}</span>
          <h2 id="separateWorksTitle" class="dialog-title">
            {{ i18n.t("works.separate_works_title") }}
          </h2>
          <div class="dialog-subtitle">{{ i18n.t("works.separate_works_help") }}</div>
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
      <div class="db separate-works-body">
        <div class="field">
          <label for="separateWorksSource">{{ i18n.t("works.source_jsonl") }}</label>
          <select id="separateWorksSource" v-model="sourceId" class="control">
            <option v-for="item in current.sources" :key="item.id" :value="item.id">
              {{ item.name }} · {{ item.recordCount.toLocaleString() }}
              {{ i18n.t("dynamic.records") }}
            </option>
          </select>
        </div>
        <div class="separate-works-list">
          <label v-for="group in source?.groups ?? []" :key="group.work" class="separate-work-row">
            <input v-model="selected" type="checkbox" :value="group.work" />
            <span>
              <b>{{ group.work }}</b>
              <small>{{ group.count.toLocaleString() }} {{ i18n.t("dynamic.records") }}</small>
            </span>
          </label>
        </div>
        <label class="check-item">
          <input v-model="removeFromSource" type="checkbox" />
          <span>{{ i18n.t("works.remove_separated") }}</span>
        </label>
        <div class="info">{{ i18n.t("works.separate_nondestructive_help") }}</div>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.cancel") }}</button>
        <button class="btn primary" type="button" :disabled="busy" @click="create()">
          {{ i18n.t("works.separate_selected") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

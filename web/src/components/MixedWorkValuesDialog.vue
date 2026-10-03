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
import { useMixedWorkValuesDialog } from "../composables/mixedWorkValuesDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useMixedWorkValuesDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const FILES_SHOWN = 3;

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

function filesLabel(files: readonly string[]) {
  const shown = files.slice(0, FILES_SHOWN).join(" · ");
  return files.length > FILES_SHOWN ? `${shown} · +${files.length - FILES_SHOWN}` : shown;
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="mixed-values-dialog"
    aria-labelledby="mixedValuesTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <span class="section-label">{{ i18n.t("works.metadata_variants") }}</span>
          <h2 id="mixedValuesTitle" class="dialog-title">{{ current.fieldLabel }}</h2>
          <div class="dialog-subtitle">
            {{ current.work }} · {{ current.values.length.toLocaleString() }}
            {{ i18n.t("works.unique_values") }} · {{ current.recordCount.toLocaleString() }}
            {{ i18n.t("dynamic.records") }}
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
      <div class="db mixed-values-body">
        <p class="note">{{ i18n.t("works.mixed_values_help") }}</p>
        <div class="mixed-values-list">
          <article v-for="(entry, index) in current.values" :key="index" class="mixed-value-row">
            <span class="mixed-value-rank">{{ index + 1 }}</span>
            <div class="mixed-value-copy">
              <b>{{ entry.text ?? i18n.t("ui.unset") }}</b>
              <small>{{ filesLabel(entry.files) }}</small>
            </div>
            <span class="mixed-value-count">
              {{ entry.count.toLocaleString() }}
              <small>{{
                entry.count === 1 ? i18n.t("dynamic.record_one") : i18n.t("dynamic.records")
              }}</small>
            </span>
          </article>
        </div>
      </div>
      <div class="da">
        <button class="btn primary" type="button" autofocus @click="close()">
          {{ i18n.t("ui.done") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

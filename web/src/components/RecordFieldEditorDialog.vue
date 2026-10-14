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
import { nextTick, reactive, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import {
  useRecordFieldEditorDialog,
  type RecordEditorField,
} from "../composables/recordFieldEditorDialog";
import { parseRecordEditorValue, recordEditorText } from "../domain/recordEditorFields";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useRecordFieldEditorDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const drafts = reactive<Record<string, { text: string; checked: boolean }>>({});
const busy = ref(false);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    for (const key of Object.keys(drafts)) delete drafts[key];
    busy.value = false;
    for (const section of request?.sections ?? [])
      for (const field of section.fields)
        drafts[field.key] = { text: recordEditorText(field), checked: field.value === true };
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

function fieldId(field: RecordEditorField) {
  return `recordField-${field.key}`;
}

async function save() {
  const request = current.value;
  if (!request || busy.value) return;
  const values: Record<string, unknown> = {};
  try {
    for (const section of request.sections)
      for (const field of section.fields) {
        const draft = drafts[field.key];
        values[field.key] = parseRecordEditorValue(field.kind, draft.text, draft.checked);
      }
  } catch (error) {
    void openMessageDialog({
      title: request.parseErrorTitle,
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
    return;
  }
  busy.value = true;
  try {
    if (await request.save(values)) close();
    else busy.value = false;
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: request.title,
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="record-field-editor-dialog"
    aria-labelledby="recordFieldEditorTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <form v-if="current" @submit.prevent="save()">
      <div class="dh">
        <div>
          <h2 id="recordFieldEditorTitle" class="dialog-title">{{ current.title }}</h2>
          <div class="dialog-subtitle">{{ current.subtitle }}</div>
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
      <div class="db editor-body">
        <div v-if="current.help" class="info">{{ current.help }}</div>
        <section v-for="section in current.sections" :key="section.title" class="editor-section">
          <h3>{{ section.title }}</h3>
          <div class="editor-grid">
            <div
              v-for="field in section.fields"
              :key="field.key"
              class="field"
              :class="{ 'field-full': field.full }"
            >
              <template v-if="field.kind === 'boolean'">
                <span :id="`${fieldId(field)}-label`" class="field-label">{{ field.label }}</span>
                <label class="boolean-control">
                  <input
                    v-model="drafts[field.key].checked"
                    type="checkbox"
                    :aria-labelledby="`${fieldId(field)}-label`"
                  />
                  <span>{{ drafts[field.key].checked ? i18n.t("ui.on") : i18n.t("ui.off") }}</span>
                </label>
              </template>
              <template v-else>
                <label :for="fieldId(field)">
                  {{ field.label }}<template v-if="field.kind === 'json'"> · JSON</template>
                </label>
                <textarea
                  v-if="field.kind === 'text' || field.kind === 'json'"
                  :id="fieldId(field)"
                  v-model="drafts[field.key].text"
                  :class="{ long: field.kind === 'text' }"
                  :spellcheck="field.kind === 'json' ? false : undefined"
                ></textarea>
                <input
                  v-else
                  :id="fieldId(field)"
                  v-model="drafts[field.key].text"
                  :type="field.kind === 'number' ? 'number' : 'text'"
                  :step="field.kind === 'number' ? 'any' : undefined"
                />
              </template>
            </div>
          </div>
        </section>
      </div>
      <div class="da">
        <div v-if="current.footerNote" class="llm-footer-note">{{ current.footerNote }}</div>
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.cancel") }}</button>
        <button class="btn primary" type="submit" :disabled="busy">{{ current.saveLabel }}</button>
      </div>
    </form>
  </dialog>
</template>

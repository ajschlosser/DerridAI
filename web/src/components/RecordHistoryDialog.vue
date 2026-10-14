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
import { useRecordHistoryDialog } from "../composables/recordHistoryDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useRecordHistoryDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const cursor = ref(0);
// The request's version list is read live; bumping this re-reads it after a restore.
const refresh = ref(0);
const busy = ref(false);

const versions = computed(() => {
  void refresh.value;
  return current.value ? current.value.versions() : [];
});
const last = computed(() => Math.max(0, versions.value.length - 1));
const index = computed(() => Math.max(0, Math.min(cursor.value, last.value)));
const version = computed(() => versions.value[index.value] ?? null);
const isCurrent = computed(() => index.value === last.value);
const changed = computed(() => {
  const request = current.value;
  const previous = versions.value[index.value - 1];
  if (!request || !previous || !version.value) return [];
  return request.changedFields(previous.record, version.value.record);
});
const text = computed(() => String(version.value?.record.text ?? ""));
const words = computed(() => (text.value.trim() ? text.value.trim().split(/\s+/).length : 0));
const preview = computed(
  () => `${text.value.slice(0, 5000)}${text.value.length > 5000 ? "…" : ""}`,
);
const meta = computed(() => {
  const selectedVersion = version.value;
  if (!selectedVersion || !current.value) return "";

  const when = selectedVersion.timestamp
    ? current.value.formatTimestamp(selectedVersion.timestamp)
    : i18n.t("records.history.before_edits");
  const source = selectedVersion.source ? ` · ${selectedVersion.source}` : "";
  const model = selectedVersion.model ? ` · ${selectedVersion.model}` : "";
  return `${when}${source}${model}`;
});

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    if (request) {
      cursor.value = Math.max(0, request.versions().length - 1);
      refresh.value++;
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

/** Runs a caller action, then re-reads the versions; an action that changed something lands on the newest. */
async function act(run: () => Promise<boolean>, afterChange: "newest" | "close") {
  if (busy.value || !current.value) return;
  busy.value = true;
  try {
    if (!(await run())) return;
    if (afterChange === "close") return close();
    refresh.value++;
    cursor.value = last.value;
  } catch (error) {
    void openMessageDialog({
      title: i18n.t("records.history.title"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="record-history-dialog"
    aria-labelledby="recordHistoryTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current && version">
      <div class="dh">
        <div>
          <h2 id="recordHistoryTitle" class="dialog-title">
            {{ i18n.t("records.history.title") }}
          </h2>
          <div class="dialog-subtitle">
            {{ current.recordId }} ·
            {{ i18n.tf("records.history.changesets", { count: versions.length - 1 }) }}
          </div>
        </div>
        <button
          class="btn icon-only"
          type="button"
          :aria-label="i18n.t('common.close')"
          :title="i18n.t('common.close')"
          @click="close()"
        >
          ×
        </button>
      </div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button
            class="btn"
            type="button"
            :disabled="index <= 0"
            :title="index <= 0 ? i18n.t('records.history.at_original') : undefined"
            @click="cursor = index - 1"
          >
            {{ i18n.t("records.history.older") }}
          </button>
          <div class="history-version-position" aria-live="polite">
            <b
              >{{ version.label
              }}<template v-if="isCurrent"> · {{ i18n.t("records.history.current") }}</template></b
            >
            <span>{{ meta }}</span>
          </div>
          <button
            class="btn"
            type="button"
            :disabled="isCurrent"
            :title="isCurrent ? i18n.t('records.history.at_newest') : undefined"
            @click="cursor = index + 1"
          >
            {{ i18n.t("records.history.newer") }}
          </button>
        </div>
        <div class="history-version-summary">
          <span
            ><b>{{ changed.length }}</b>
            {{ i18n.tf("records.history.fields_changed", { count: changed.length }) }}</span
          >
          <span
            ><b>{{ words }}</b> {{ i18n.t("records.history.words") }}</span
          >
          <span
            ><b>{{ text.length.toLocaleString() }}</b>
            {{ i18n.t("records.history.characters") }}</span
          >
        </div>
        <div v-if="changed.length" class="history-version-diffs">
          <details v-for="field in changed" :key="field" class="history-version-diff">
            <summary>
              <b>{{ current.fieldLabel(field) }}</b
              ><span>{{ i18n.t("records.history.changed") }}</span>
            </summary>
            <div class="history-diff-values">
              <div>
                <small>{{ i18n.t("records.history.previous") }}</small>
                <pre>{{ current.formatValue(versions[index - 1]?.record?.[field]) }}</pre>
              </div>
              <div>
                <small>{{ i18n.t("records.history.this_version") }}</small>
                <pre>{{ current.formatValue(version.record[field]) }}</pre>
              </div>
            </div>
          </details>
        </div>
        <div v-else class="info">{{ i18n.t("records.history.original_state") }}</div>
        <details class="history-record-preview">
          <summary>{{ i18n.t("records.history.preview") }}</summary>
          <div class="history-preview-meta">
            <b>{{ version.record.work || i18n.t("records.history.untitled") }}</b>
            <span
              >{{ version.record.document_author || "" }} · {{ version.record.year || "" }}</span
            >
          </div>
          <div class="history-preview-text">{{ preview }}</div>
        </details>
      </div>
      <div class="da record-history-actions">
        <button
          class="btn danger secondary-danger"
          type="button"
          :disabled="busy"
          @click="act(() => current!.clear(), 'close')"
        >
          {{ i18n.t("records.history.delete_audit") }}
        </button>
        <span class="dialog-action-spacer"></span>
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.close") }}</button>
        <button
          class="btn"
          type="button"
          :disabled="busy || (index === 0 && isCurrent)"
          @click="act(() => current!.restoreOriginal(), 'newest')"
        >
          {{ i18n.t("records.history.restore_original") }}
        </button>
        <button
          class="btn primary"
          type="button"
          :disabled="busy || isCurrent"
          :title="isCurrent ? i18n.t('records.history.already_current') : undefined"
          @click="act(() => current!.restore(version!), 'newest')"
        >
          {{ i18n.t("records.history.restore_version") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

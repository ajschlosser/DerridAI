<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { useUpsertQueueDialog, type UpsertQueueItem } from "../composables/upsertQueueDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useUpsertQueueDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const items = ref<UpsertQueueItem[]>([]);
const unchecked = ref<Set<string>>(new Set());
const expanded = ref<Set<string>>(new Set());

function refresh() {
  items.value = current.value?.items() ?? [];
}

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    unchecked.value = new Set();
    expanded.value = new Set();
    refresh();
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

function flip(set: Set<string>, key: string) {
  const next = new Set(set);
  if (!next.delete(key)) next.add(key);
  return next;
}
const toggleChecked = (key: string) => (unchecked.value = flip(unchecked.value, key));
const toggleExpanded = (key: string) => (expanded.value = flip(expanded.value, key));

function selectAll(on: boolean) {
  unchecked.value = on ? new Set() : new Set(items.value.map((item) => item.key));
}

function remove(key: string) {
  current.value?.remove(key);
  refresh();
}

async function sync() {
  const request = current.value;
  if (!request) return;
  const keys = items.value.filter((item) => !unchecked.value.has(item.key)).map((i) => i.key);
  if (!keys.length) {
    toast(i18n.t("records.toast.select_queued"), { tone: "warning" });
    return;
  }
  close();
  try {
    await request.sync(keys);
  } catch (error) {
    void openMessageDialog({
      title: i18n.t("vector.unsynced_changes"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="queue-dialog wide-queue-dialog"
    aria-labelledby="upsertQueueTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="upsertQueueTitle" class="dialog-title">
            {{ i18n.t("vector.unsynced_changes") }}
          </h2>
          <div class="dialog-subtitle">
            {{ current.store }} · {{ items.length }} {{ i18n.t("dynamic.records") }}
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
      <div class="db">
        <div class="queue-explainer">
          <b>{{ i18n.t("vector.unsynced_changes_what") }}</b>
          <p>{{ i18n.t("vector.unsynced_changes_help") }}</p>
        </div>
        <div class="queue-bulk-actions">
          <template v-if="items.length">
            <button class="btn small" type="button" @click="selectAll(true)">
              {{ i18n.t("ui.select_all") }}
            </button>
            <button class="btn small" type="button" @click="selectAll(false)">
              {{ i18n.t("ui.clear_selection") }}
            </button>
          </template>
        </div>
        <div class="upsert-queue-list">
          <section v-for="item in items" :key="item.key" class="upsert-queue-card">
            <div class="upsert-queue-head">
              <label class="upsert-queue-item">
                <input
                  type="checkbox"
                  :checked="!unchecked.has(item.key)"
                  @change="toggleChecked(item.key)"
                />
                <span
                  ><b>{{ item.recordId }}</b
                  ><small>{{ item.source }}</small></span
                >
                <span class="db-status" :class="item.status.kind"
                  ><i></i>{{ item.status.label }}</span
                >
              </label>
              <div class="tools">
                <button
                  class="btn small"
                  type="button"
                  :aria-expanded="expanded.has(item.key)"
                  :aria-controls="`queueChanges-${item.key}`"
                  @click="toggleExpanded(item.key)"
                >
                  {{ i18n.tf("records.upsert.review_n", { count: item.changes.length }) }}
                </button>
                <button class="btn small danger" type="button" @click="remove(item.key)">
                  {{ i18n.t("records.upsert.remove") }}
                </button>
              </div>
            </div>
            <div
              v-show="expanded.has(item.key)"
              :id="`queueChanges-${item.key}`"
              class="queue-change-list"
            >
              <div v-for="(change, n) in item.changes" :key="n" class="queue-change-row">
                <b>{{ change.field }}</b>
                <span
                  >{{ change.source
                  }}<template v-if="change.when"> · {{ change.when }}</template></span
                >
                <details>
                  <summary>{{ i18n.t("records.upsert.values") }}</summary>
                  <div class="queue-change-values">
                    <pre>{{ change.oldValue }}</pre>
                    <span>→</span>
                    <pre>{{ change.newValue }}</pre>
                  </div>
                </details>
              </div>
            </div>
          </section>
          <div v-if="!items.length" class="llm-empty">
            {{ i18n.t("vector.no_unsynced_changes") }}
          </div>
        </div>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.close") }}</button>
        <button v-if="items.length" class="btn primary" type="button" @click="sync()">
          {{ i18n.t("vector.sync_selected") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

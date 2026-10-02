<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import {
  useBulkFieldEditorDialog,
  type BulkFieldScope,
} from "../composables/bulkFieldEditorDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useBulkFieldEditorDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const scope = ref<BulkFieldScope>("active");
const field = ref("");
const text = ref("");
const onlyDifferent = ref(true);
const busy = ref(false);
let lastHintField = "";

const hint = computed(() => {
  const request = current.value;
  if (!request || !field.value) return "";
  const { targets, distinct } = request.inspect(scope.value, field.value);
  return i18n.tf("records.bulk.hint", {
    targets: targets.toLocaleString(),
    values: distinct,
    sampled: distinct > 8 ? i18n.t("records.bulk.sampled", " (sampled)") : "",
  });
});

// Prefill the value when every record agrees, and clear it when the field changes to one where they differ.
function prefill() {
  const request = current.value;
  if (!request || !field.value) return;
  const { distinct, only } = request.inspect(scope.value, field.value);
  if (distinct === 1 && (lastHintField !== field.value || !text.value.trim())) {
    text.value = only ?? "";
  } else if (lastHintField !== field.value && distinct !== 1) {
    text.value = "";
  }
  lastHintField = field.value;
}

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    scope.value = request?.defaultScope ?? "active";
    field.value = request?.fields[0]?.id ?? "";
    text.value = "";
    onlyDifferent.value = true;
    busy.value = false;
    lastHintField = "";
    prefill();
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

async function apply() {
  const request = current.value;
  if (!request || busy.value) return;
  busy.value = true;
  try {
    const ok = await request.apply({ scope: scope.value, field: field.value, text: text.value });
    if (ok) close();
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
    class="bulk-field-dialog"
    aria-labelledby="bulkFieldTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="bulkFieldTitle" class="dialog-title">{{ current.title }}</h2>
          <div class="dialog-subtitle">{{ i18n.t("records.bulk.subtitle") }}</div>
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
      <div class="db bulk-field-body">
        <div v-if="current.fixedCount !== null" class="info">
          {{ i18n.tf("records.bulk.in_operation", { count: current.fixedCount.toLocaleString() }) }}
        </div>
        <div v-else class="field">
          <label for="bulkFieldScope">{{ i18n.t("records.bulk.target") }}</label>
          <select id="bulkFieldScope" v-model="scope" class="control" @change="prefill()">
            <option value="selected" :disabled="!current.selectedCount">
              {{
                i18n.tf("records.bulk.selected", {
                  count: current.selectedCount.toLocaleString(),
                })
              }}
            </option>
            <option value="active">
              {{ i18n.tf("records.bulk.active", { count: current.activeCount.toLocaleString() }) }}
            </option>
            <option v-if="current.currentWork" value="work">
              {{ i18n.tf("records.bulk.work", { work: current.currentWork }) }}
            </option>
            <option value="all">
              {{ i18n.tf("records.bulk.all", { count: current.allCount.toLocaleString() }) }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="bulkFieldName">{{ i18n.t("works.field") }}</label>
          <select id="bulkFieldName" v-model="field" class="control" @change="prefill()">
            <option v-for="option in current.fields" :key="option.id" :value="option.id">
              {{ option.label }} · {{ option.id }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="bulkFieldValue">{{ i18n.t("records.bulk.new_value") }}</label>
          <textarea
            id="bulkFieldValue"
            v-model="text"
            spellcheck="false"
            :placeholder="i18n.t('records.bulk.placeholder')"
          ></textarea>
          <div id="bulkFieldHint" class="note" role="status">{{ hint }}</div>
        </div>
        <label class="check-item">
          <input v-model="onlyDifferent" type="checkbox" />
          <span>{{ i18n.t("records.bulk.only_different") }}</span>
        </label>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.cancel") }}</button>
        <button class="btn primary" type="button" :disabled="busy" @click="apply()">
          {{ i18n.t("records.bulk.apply") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

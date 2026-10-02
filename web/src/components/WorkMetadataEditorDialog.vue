<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { useWorkMetadataEditorDialog } from "../composables/workMetadataEditor";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useWorkMetadataEditorDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const values = ref<Record<string, string>>({});
const applied = ref<string[]>([]);
const busy = ref(false);

// The help text names three literal terms; split them out so they render as emphasis without raw HTML.
const MARK = "\u0001";
const helpParts = computed(() =>
  i18n
    .tf("works.edit_metadata_apply_help", {
      apply: `${MARK}b:${i18n.t("common.apply")}${MARK}`,
      work: `${MARK}code:work${MARK}`,
      updates: `${MARK}code:updates${MARK}`,
    })
    .split(MARK)
    .map((part, index) =>
      index % 2 === 1
        ? { tag: part.slice(0, part.indexOf(":")), text: part.slice(part.indexOf(":") + 1) }
        : { tag: "", text: part },
    ),
);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    values.value = Object.fromEntries((request?.fields ?? []).map((f) => [f.field, f.initial]));
    applied.value = [];
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

function placeholder(mixed: boolean, json: boolean) {
  if (!mixed) return json ? i18n.t("works.json_value") : "";
  return json ? i18n.t("works.mixed_values_json") : i18n.t("works.mixed_values");
}

async function apply() {
  const request = current.value;
  if (!request || busy.value) return;
  if (!applied.value.length) {
    toast(i18n.t("works.select_field_to_apply"), { tone: "warning" });
    return;
  }
  busy.value = true;
  try {
    const picked = Object.fromEntries(applied.value.map((field) => [field, values.value[field]]));
    if (await request.apply({ values: picked })) close();
    else busy.value = false;
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: i18n.t("works.apply_metadata"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="work-metadata-dialog"
    aria-labelledby="workMetadataTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="workMetadataTitle" class="dialog-title">
            {{ i18n.t("works.edit_work_metadata") }}
          </h2>
          <div class="dialog-subtitle">
            {{ current.work }} ·
            {{
              i18n.tf("works.associated_records_files", {
                records: current.recordCount.toLocaleString(),
                files: current.fileCount,
              })
            }}
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
      <div class="db work-metadata-body">
        <div class="info">
          <template v-for="(part, index) in helpParts" :key="index">
            <b v-if="part.tag === 'b'">{{ part.text }}</b>
            <code v-else-if="part.tag === 'code'">{{ part.text }}</code>
            <template v-else>{{ part.text }}</template>
          </template>
        </div>
        <div class="work-meta-table">
          <div v-for="item in current.fields" :key="item.field" class="work-meta-row">
            <label class="work-meta-apply">
              <input v-model="applied" type="checkbox" :value="item.field" />
              <span>{{ i18n.t("ui.apply") }}</span>
            </label>
            <div class="work-meta-field">
              <b>{{ item.label }}</b>
              <button
                v-if="item.mixed"
                type="button"
                class="mixed-value-inspect compact"
                :aria-label="
                  i18n.tf('works.inspect_mixed_aria', { count: item.mixedCount, field: item.label })
                "
                @click="current.inspectMixed(item.field)"
              >
                <span>{{ i18n.t("works.mixed") }}</span>
                <b>{{ item.mixedCount }}</b>
                <small>{{ i18n.t("works.unique_values") }}</small>
              </button>
            </div>
            <select
              v-if="item.kind === 'boolean'"
              v-model="values[item.field]"
              class="control work-meta-value"
              :aria-label="item.label"
            >
              <option value="">
                {{ item.mixed ? i18n.t("works.mixed_leave_unchanged") : i18n.t("works.unset") }}
              </option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
            <textarea
              v-else-if="item.kind === 'json' || item.kind === 'textarea'"
              v-model="values[item.field]"
              class="work-meta-value"
              :class="{ 'work-meta-json': item.kind === 'json' }"
              :aria-label="item.label"
              :placeholder="placeholder(item.mixed, item.kind === 'json')"
            ></textarea>
            <input
              v-else
              :value="values[item.field]"
              @input="values[item.field] = ($event.target as HTMLInputElement).value"
              class="control work-meta-value"
              :type="item.kind === 'number' ? 'number' : 'text'"
              :aria-label="item.label"
              :placeholder="placeholder(item.mixed, false)"
            />
          </div>
        </div>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.cancel") }}</button>
        <button class="btn primary" type="button" :disabled="busy" @click="apply()">
          {{
            busy
              ? i18n.t("works.applying_metadata")
              : i18n.tf("works.apply_selected_to_records", {
                  count: current.recordCount.toLocaleString(),
                })
          }}
        </button>
      </div>
    </template>
  </dialog>
</template>

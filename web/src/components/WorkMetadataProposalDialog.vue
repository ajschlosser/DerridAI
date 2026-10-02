<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { useWorkMetadataProposalDialog } from "../composables/workMetadataProposalDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useWorkMetadataProposalDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const selected = ref<boolean[]>([]);
const values = ref<string[]>([]);
const busy = ref(false);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    selected.value = (request?.entries ?? []).map(() => true);
    values.value = (request?.entries ?? []).map((entry) => entry.proposed);
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

function setAll(value: boolean) {
  selected.value = selected.value.map(() => value);
}

async function apply() {
  const request = current.value;
  if (!request || busy.value) return;
  const picks = request.entries
    .map((_, index) => index)
    .filter((index) => selected.value[index])
    .map((index) => ({ index, value: values.value[index] }));
  if (!picks.length) {
    toast(i18n.t("works.select_metadata_changes"), { tone: "warning" });
    return;
  }
  busy.value = true;
  try {
    if (await request.apply(picks)) close();
    else busy.value = false;
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: i18n.t("works.apply_selected_metadata"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="work-metadata-proposal-dialog"
    aria-labelledby="workProposalTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="workProposalTitle" class="dialog-title">
            {{ i18n.t("works.review_metadata_proposals") }}
          </h2>
          <div class="dialog-subtitle">
            {{ current.jobLabel }} · {{ current.entries.length.toLocaleString() }}
            {{ i18n.t("works.proposed_field_changes") }}
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
      <div class="db work-proposal-body">
        <div v-if="current.unmatched.length" class="info warn">
          {{ i18n.tf("works.metadata_no_match_count", { count: current.unmatched.length }) }}
        </div>
        <div class="work-proposal-toolbar">
          <button class="btn small" type="button" @click="setAll(true)">
            {{ i18n.t("ui.select_all") }}
          </button>
          <button class="btn small" type="button" @click="setAll(false)">
            {{ i18n.t("ui.clear") }}
          </button>
          <span class="note">{{ i18n.t("works.proposal_edit_help") }}</span>
        </div>
        <div v-if="current.entries.length" class="work-proposal-table-wrap">
          <table class="work-proposal-table">
            <thead>
              <tr>
                <th scope="col">
                  <span class="sr-only">{{ i18n.t("ui.select_all") }}</span>
                </th>
                <th scope="col">{{ i18n.t("nav.works") }}</th>
                <th scope="col">{{ i18n.t("works.field") }}</th>
                <th scope="col">{{ i18n.t("works.current_value") }}</th>
                <th scope="col">{{ i18n.t("works.proposed_value") }}</th>
                <th scope="col">{{ i18n.t("works.source_reason") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(entry, index) in current.entries" :key="index">
                <td>
                  <input
                    v-model="selected[index]"
                    type="checkbox"
                    :aria-label="`${entry.work} · ${entry.fieldLabel}`"
                  />
                </td>
                <td>
                  <b>{{ entry.work }}</b>
                  <small
                    >{{ entry.recordCount.toLocaleString() }} {{ i18n.t("dynamic.records") }}</small
                  >
                </td>
                <td>{{ entry.fieldLabel }}</td>
                <td>
                  <div class="proposal-current">{{ entry.current }}</div>
                </td>
                <td>
                  <textarea
                    v-model="values[index]"
                    class="control proposal-value"
                    rows="2"
                    :aria-label="`${entry.work} · ${entry.fieldLabel} · ${i18n.t('works.proposed_value')}`"
                  ></textarea>
                </td>
                <td>
                  <small>{{ entry.rationale || i18n.t("works.catalogue_selected") }}</small>
                  <span v-if="entry.confidence != null" class="proposal-confidence"
                    >{{ Math.round(entry.confidence * 100) }}%</span
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="llm-empty">{{ i18n.t("works.no_metadata_changes") }}</div>
        <details v-if="current.unmatched.length" class="work-proposal-errors">
          <summary>{{ i18n.t("works.unmatched_works") }}</summary>
          <div v-for="(item, index) in current.unmatched" :key="index">
            <b>{{ item.work }}</b
            ><span>{{ item.message || i18n.t("works.no_catalogue_match") }}</span>
          </div>
        </details>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.close") }}</button>
        <button
          class="btn primary"
          type="button"
          :disabled="busy || !current.entries.length"
          @click="apply()"
        >
          {{ busy ? i18n.t("works.applying_metadata") : i18n.t("works.apply_selected_metadata") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

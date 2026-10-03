<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useJobDetailsDialog } from "../composables/jobDetailsDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useJobDetailsDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);

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

async function cancelJob() {
  const request = current.value;
  close();
  await request?.onCancel();
}

async function openResult() {
  const action = current.value?.openResult;
  close();
  await action?.run();
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="job-details-dialog"
    aria-labelledby="jobDetailsTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="jobDetailsTitle" class="dialog-title">{{ current.title }}</h2>
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
      <div class="db job-details-body">
        <section class="job-detail-summary">
          <div v-for="fact in current.facts" :key="fact.name">
            <span>{{ fact.name }}</span
            ><b>{{ fact.value }}</b>
          </div>
        </section>
        <div v-if="current.fatalError" class="info error" role="alert">
          {{ current.fatalError }}
        </div>
        <section class="card-inset">
          <div class="rag-result-section-head">
            <div>
              <b>{{ i18n.t("operations.request_config") }}</b>
              <div class="note">{{ i18n.t("operations.api_keys_omitted") }}</div>
            </div>
          </div>
          <pre class="job-detail-json">{{ current.requestJson }}</pre>
        </section>
        <section class="card-inset">
          <div class="rag-result-section-head">
            <div>
              <b>{{ i18n.t("operations.timeline") }}</b>
              <div class="note">
                {{ i18n.tf("operations.recorded_events", { count: current.events.length }) }}
              </div>
            </div>
          </div>
          <div class="job-event-list">
            <div
              v-for="(event, index) in current.events"
              :key="index"
              class="job-event"
              :class="{ latest: event.latest }"
            >
              <time>{{ event.when }}</time>
              <b>{{ event.stage }}</b>
              <span>{{ event.detail }}</span>
            </div>
            <div v-if="!current.events.length" class="note">
              {{ i18n.t("operations.no_events") }}
            </div>
          </div>
        </section>
        <section class="card-inset">
          <div class="rag-result-section-head">
            <b>{{ i18n.t("operations.result_summary") }}</b>
          </div>
          <pre class="job-detail-json">{{ current.resultJson }}</pre>
        </section>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.close") }}</button>
        <button v-if="current.cancel === 'cancelling'" class="btn" type="button" disabled>
          {{ i18n.t("operations.cancelling") }}
        </button>
        <button
          v-else-if="current.cancel === 'cancel'"
          class="btn danger"
          type="button"
          @click="cancelJob()"
        >
          {{ i18n.t("operations.cancel_operation") }}
        </button>
        <button v-if="current.openResult" class="btn primary" type="button" @click="openResult()">
          {{ current.openResult.label }}
        </button>
      </div>
    </template>
  </dialog>
</template>

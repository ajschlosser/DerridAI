<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useLlmToolResultDialog } from "../composables/llmToolResultDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useLlmToolResultDialog();
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

async function runAction() {
  const action = current.value?.action;
  close();
  await action?.run();
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="llm-tool-result-dialog"
    aria-labelledby="llmToolResultTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="llmToolResultTitle" class="dialog-title">{{ current.title }}</h2>
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
      <div class="db">
        <section v-if="current.body.kind === 'clean_text'" class="card-inset">
          <div class="cardhead">
            <b>{{ i18n.t("jobs.tool.cleaned_text") }}</b>
          </div>
          <pre class="llm-tool-text">{{ current.body.text }}</pre>
        </section>
        <pre v-else-if="current.body.kind === 'draft_record'" class="rag-json">{{
          current.body.json
        }}</pre>
        <div v-else-if="current.body.kind === 'link_record'" class="llm-tool-match">
          <b>{{ current.body.recordId || i18n.t("jobs.tool.no_match") }}</b>
          <p>{{ current.body.reason }}</p>
        </div>
        <template v-else-if="current.body.kind === 'rag_grade'">
          <section v-if="current.body.question" class="llm-tool-context">
            <span>{{ i18n.t("jobs.tool.question") }}</span>
            <p>{{ current.body.question }}</p>
          </section>
          <div v-if="current.body.cacheError" class="info warn" role="status">
            {{ i18n.tf("jobs.tool.grade_cache_failed", { error: current.body.cacheError }) }}
          </div>
          <!-- eslint-disable-next-line vue/no-v-html -- escaped by the shared grade renderer -->
          <div v-html="current.body.gradeHtml"></div>
        </template>
        <section v-else-if="current.body.kind === 'rag_grade_batch'" class="bulk-grade-result">
          <div class="compare-result-summary">
            <div>
              <strong>{{ current.body.graded.toLocaleString() }}</strong>
              <span>{{ i18n.t("jobs.tool.graded") }}</span>
            </div>
            <div>
              <strong>{{ current.body.failed.toLocaleString() }}</strong>
              <span>{{ i18n.t("jobs.tool.failed") }}</span>
            </div>
            <div>
              <strong>{{ current.body.total.toLocaleString() }}</strong>
              <span>{{ i18n.t("jobs.tool.responses") }}</span>
            </div>
          </div>
          <details v-if="current.body.errorCount">
            <summary>
              {{ i18n.tf("jobs.tool.errors_n", { count: current.body.errorCount }) }}
            </summary>
            <pre class="rag-json">{{ current.body.errorsJson }}</pre>
          </details>
          <div v-else class="info">{{ i18n.t("jobs.tool.all_processed") }}</div>
        </section>
        <pre v-else class="rag-json">{{ current.body.json }}</pre>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("common.close") }}</button>
        <button v-if="current.action" class="btn primary" type="button" @click="runAction()">
          {{ current.action.label }}
        </button>
      </div>
    </template>
  </dialog>
</template>

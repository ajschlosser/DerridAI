<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import type { CorpusBuild } from "../api/pdfCorpus";

const props = defineProps<{ build: CorpusBuild; disabled?: boolean }>();
const emit = defineEmits<{ "run-another": []; stop: [] }>();
const i18n = useI18nStore();
const dismissedId = ref("");
const operation = computed(() => props.build.metadata_operation || {});
const isPass = computed(
  () =>
    operation.value.kind === "metadata_enrichment_rerun" &&
    operation.value.operation_id !== dismissedId.value,
);
const state = computed(() => String(operation.value.state || ""));
const running = computed(() => ["queued", "running"].includes(state.value));
const passesRun = computed(() => Number(operation.value.passes_completed || 0));
const currentPass = computed(() => Math.max(1, Number(operation.value.current_pass || 1)));
const totalPasses = computed(() => Math.max(1, Number(operation.value.passes_requested || 1)));
// Counters are cumulative across a chain; the bar shows only the current pass.
const processedThisPass = computed(() => {
  const earlier = (operation.value.pass_results || []).reduce(
    (sum, pass) => sum + Number(pass.records_processed || 0),
    0,
  );
  return Math.max(0, Number(operation.value.records_processed || 0) - earlier);
});
const passTotal = computed(() => Math.max(1, Number(operation.value.records_total || 0)));
const changes = computed(() => ({
  added: (operation.value.pass_results || []).reduce(
    (sum, pass) => sum + Number(pass.fields_added || 0),
    0,
  ),
  replaced: Number(operation.value.fields_replaced || 0),
  kept: Number(operation.value.fields_kept || 0),
  disputed: Number(operation.value.records_disputed || 0),
}));
const heading = computed(() => {
  if (running.value)
    return i18n.tf("pdf_corpus.enrichment_pass_running", "Pass {current} of {total} is running", {
      current: currentPass.value,
      total: totalPasses.value,
    });
  if (state.value === "failed")
    return i18n.t("pdf_corpus.enrichment_pass_failed", "Enrichment failed");
  if (state.value === "cancelled")
    return i18n.tf(
      "pdf_corpus.enrichment_pass_cancelled",
      "Enrichment was stopped. Passes completed: {passes}.",
      { passes: passesRun.value },
    );
  return i18n.tf(
    "pdf_corpus.enrichment_pass_complete",
    "Enrichment finished. Passes run: {passes}.",
    { passes: passesRun.value },
  );
});
</script>

<template>
  <section
    v-if="isPass"
    class="pass-status"
    :data-state="state"
    role="status"
    aria-live="polite"
    aria-labelledby="pass-status-title"
  >
    <div class="pass-copy">
      <span class="eyebrow">{{
        i18n.t("pdf_corpus.enrichment_status_title", "Metadata enrichment")
      }}</span>
      <b id="pass-status-title">{{ heading }}</b>
      <template v-if="running">
        <progress
          :max="passTotal"
          :value="processedThisPass"
          :aria-label="
            i18n.tf(
              'pdf_corpus.enrichment_pass_progress',
              '{processed} of {total} records checked in this pass',
              { processed: processedThisPass, total: passTotal },
            )
          "
        ></progress>
        <span>{{
          i18n.tf(
            "pdf_corpus.enrichment_pass_progress",
            "{processed} of {total} records checked in this pass",
            { processed: processedThisPass, total: passTotal },
          )
        }}</span>
        <small>{{
          i18n.t(
            "pdf_corpus.enrichment_keep_working",
            "You can keep reviewing while this runs. New suggestions appear in the queue as they arrive.",
          )
        }}</small>
      </template>
      <span v-else-if="state === 'failed'">{{ operation.error }}</span>
      <template v-else>
        <span>{{
          i18n.tf(
            "pdf_corpus.enrichment_pass_changes",
            "Values added: {added} · replaced: {replaced} · kept: {kept} · records with disagreements: {disputed}",
            changes,
          )
        }}</span>
        <small v-if="operation.converged">{{
          i18n.t(
            "pdf_corpus.enrichment_pass_converged",
            "Stopped early because the last pass found nothing new.",
          )
        }}</small>
      </template>
    </div>
    <div class="pass-actions">
      <UiButton
        v-if="running"
        :label="i18n.t('pdf_corpus.enrichment_stop', 'Stop enrichment')"
        :disabled="disabled"
        @click="emit('stop')"
      />
      <template v-else>
        <UiButton
          variant="primary"
          :label="i18n.t('pdf_corpus.enrichment_run_another', 'Run another pass')"
          :disabled="disabled"
          @click="emit('run-another')"
        />
        <UiButton
          :label="i18n.t('pdf_corpus.enrichment_dismiss', 'Dismiss')"
          @click="dismissedId = String(operation.operation_id || '')"
        />
      </template>
    </div>
  </section>
</template>

<style scoped>
.pass-status {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.pass-status[data-state="failed"] {
  border-color: var(--danger);
  background: var(--danger-bg);
}
.pass-copy {
  display: grid;
  gap: 4px;
  min-inline-size: 0;
  flex: 1 1 320px;
}
.eyebrow {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 800;
}
.pass-copy b {
  font-size: 0.9375rem;
}
.pass-copy span,
.pass-copy small {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.5;
}
progress {
  inline-size: min(360px, 100%);
  block-size: 8px;
  accent-color: var(--accent);
}
.pass-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>

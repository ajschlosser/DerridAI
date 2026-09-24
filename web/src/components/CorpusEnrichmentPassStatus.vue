<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import type { CorpusBuild } from "../api/pdfCorpus";

const ENRICHMENT_KINDS = new Set(["metadata_enrichment", "metadata_enrichment_rerun"]);

const props = defineProps<{ build: CorpusBuild; disabled?: boolean }>();
const emit = defineEmits<{ "run-another": []; stop: [] }>();
const i18n = useI18nStore();
const dismissedId = ref("");
const operation = computed(() => props.build.metadata_operation || {});
const status = computed(() => String(props.build.status || ""));
const stage = computed(() => String(props.build.stage || ""));
const buildRunning = computed(() => ["queued", "running"].includes(status.value));
const initialEnriching = computed(() => buildRunning.value && stage.value === "enriching");
const isEnrichmentOp = computed(
  () =>
    ENRICHMENT_KINDS.has(String(operation.value.kind || "")) &&
    String(operation.value.operation_id || "") !== dismissedId.value,
);
const idleReady = computed(() => {
  if (initialEnriching.value || buildRunning.value) return false;
  if (props.build.publication) return false;
  if (Number(props.build.record_count || 0) <= 0) return false;
  return ["awaiting_review", "ready", "blocked"].includes(status.value) || stage.value === "review";
});
const visible = computed(() => !initialEnriching.value && (isEnrichmentOp.value || idleReady.value));
const state = computed(() => String(operation.value.state || ""));
const running = computed(() => isEnrichmentOp.value && ["queued", "running"].includes(state.value));
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
    return i18n.tf("pdf_corpus.enrichment_pass_running", {
      current: currentPass.value,
      total: totalPasses.value,
    });
  if (isEnrichmentOp.value && state.value === "failed")
    return i18n.t("pdf_corpus.enrichment_pass_failed");
  if (isEnrichmentOp.value && state.value === "cancelled")
    return i18n.tf("pdf_corpus.enrichment_pass_cancelled", { passes: passesRun.value });
  if (isEnrichmentOp.value)
    return i18n.tf("pdf_corpus.enrichment_pass_complete", { passes: passesRun.value });
  return i18n.t("pdf_corpus.enrichment_pass_idle");
});
</script>

<template>
  <section
    v-if="visible"
    class="pass-status"
    :data-state="running ? state : isEnrichmentOp ? state : 'idle'"
    role="status"
    aria-live="polite"
    aria-labelledby="pass-status-title"
  >
    <div class="pass-copy">
      <span class="eyebrow">{{
        i18n.t("pdf_corpus.enrichment_status_title")
      }}</span>
      <b id="pass-status-title">{{ heading }}</b>
      <template v-if="running">
        <progress
          :max="passTotal"
          :value="processedThisPass"
          :aria-label="
            i18n.tf('pdf_corpus.enrichment_pass_progress', { processed: processedThisPass, total: passTotal })
          "
        ></progress>
        <span>{{
          i18n.tf("pdf_corpus.enrichment_pass_progress", { processed: processedThisPass, total: passTotal })
        }}</span>
        <small>{{
          i18n.t("pdf_corpus.enrichment_keep_working")
        }}</small>
        <small v-if="operation.current_record_id">{{
          i18n.tf("pdf_corpus.enrichment_current_task", { record: operation.current_record_id, task: operation.current_task || i18n.t("pdf_corpus.metadata_enrichment") })
        }}</small>
        <small v-if="(operation.active_tasks || []).length > 1">{{
          i18n.tf("pdf_corpus.enrichment_active_tasks", { count: operation.active_tasks?.length || 0 })
        }}</small>
      </template>
      <span v-else-if="isEnrichmentOp && state === 'failed'">{{ operation.error }}</span>
      <template v-else-if="isEnrichmentOp">
        <span>{{
          i18n.tf("pdf_corpus.enrichment_pass_changes", changes)
        }}</span>
        <small v-if="operation.converged">{{
          i18n.t("pdf_corpus.enrichment_pass_converged")
        }}</small>
      </template>
      <small v-else>{{
        i18n.t("pdf_corpus.enrichment_pass_idle_help")
      }}</small>
    </div>
    <div class="pass-actions">
      <UiButton
        v-if="running"
        :label="i18n.t('pdf_corpus.enrichment_stop')"
        :disabled="disabled"
        @click="emit('stop')"
      />
      <template v-else>
        <UiButton
          variant="primary"
          :label="i18n.t('pdf_corpus.enrichment_run_another')"
          :disabled="disabled"
          @click="emit('run-another')"
        />
        <UiButton
          v-if="isEnrichmentOp"
          :label="i18n.t('pdf_corpus.enrichment_dismiss')"
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

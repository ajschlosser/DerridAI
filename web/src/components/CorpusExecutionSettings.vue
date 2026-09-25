<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(
  defineProps<{
    generation?: Record<string, unknown>;
    stageLimits?: Record<string, number>;
    stageTimeouts?: Record<string, number>;
    maxConcurrentRequests?: number;
    useProfileDefaults?: boolean;
    disabled?: boolean;
  }>(),
  {
    generation: () => ({}),
    stageLimits: () => ({}),
    stageTimeouts: () => ({}),
    maxConcurrentRequests: 1,
    useProfileDefaults: true,
    disabled: false,
  },
);
const emit = defineEmits<{
  (event: "update:generation", value: Record<string, unknown>): void;
  (event: "update:stageLimits", value: Record<string, number>): void;
  (event: "update:stageTimeouts", value: Record<string, number>): void;
  (event: "update:maxConcurrentRequests", value: number): void;
  (event: "update:useProfileDefaults", value: boolean): void;
}>();
const i18n = useI18nStore();
const defaults = {
  manifest_num_predict: 1800,
  segmentation_num_predict: 1200,
  reconciliation_num_predict: 1000,
  discourse_num_predict: 1600,
  quotation_num_predict: 1500,
  indexing_num_predict: 1200,
  segmentation_window_tokens: 5000,
};
const timeoutDefaults = {
  manifest: 300,
  segmentation: 300,
  reconciliation: 240,
  discourse: 240,
  quotation: 240,
  indexing: 180,
};
const numCtx = computed(() => Number(props.generation?.num_ctx || 0));
const requiredContext = computed(
  () =>
    Number(props.stageLimits?.segmentation_window_tokens || defaults.segmentation_window_tokens) +
    Number(props.stageLimits?.segmentation_num_predict || defaults.segmentation_num_predict) +
    1536,
);
const contextSafe = computed(() => !numCtx.value || requiredContext.value <= numCtx.value);
function numericGeneration(
  key: string,
  event: Event,
  { integer = false, min }: { integer?: boolean; min?: number } = {},
) {
  const raw = (event.target as HTMLInputElement).value;
  const next = { ...props.generation };
  if (raw === "") delete next[key];
  else {
    let value = Number(raw);
    if (!Number.isFinite(value)) return;
    if (integer) value = Math.trunc(value);
    if (min !== undefined) value = Math.max(min, value);
    next[key] = value;
  }
  emit("update:generation", next);
}
function thinkingGeneration(event: Event) {
  const raw = (event.target as HTMLSelectElement).value;
  const value: boolean | "low" | "medium" | "high" =
    raw === "true" ? true : raw === "false" ? false : (raw as "low" | "medium" | "high");
  emit("update:generation", { ...props.generation, think: value });
}
function stage(key: string, event: Event) {
  const value = Math.trunc(Number((event.target as HTMLInputElement).value));
  if (!Number.isFinite(value)) return;
  emit("update:stageLimits", { ...defaults, ...props.stageLimits, [key]: value });
}
function stageTimeout(key: string, event: Event) {
  const value = Math.max(
    30,
    Math.min(
      1800,
      Math.trunc(
        Number((event.target as HTMLInputElement).value) ||
          timeoutDefaults[key as keyof typeof timeoutDefaults],
      ),
    ),
  );
  emit("update:stageTimeouts", { ...timeoutDefaults, ...props.stageTimeouts, [key]: value });
}
function concurrent(event: Event) {
  const value = Math.max(
    1,
    Math.min(16, Math.trunc(Number((event.target as HTMLInputElement).value) || 1)),
  );
  emit("update:maxConcurrentRequests", value);
}
</script>

<template>
  <details class="execution-settings-shell" :open="!props.useProfileDefaults || !contextSafe">
    <summary class="execution-settings-summary">
      <span>{{ i18n.t("pdf_corpus.execution_settings") }}</span>
      <small v-if="props.useProfileDefaults && contextSafe">{{
        i18n.t("pdf_corpus.execution_settings_using_defaults")
      }}</small>
      <small v-else-if="!contextSafe">{{ i18n.t("pdf_corpus.context_unsafe") }}</small>
      <small v-else>{{ i18n.t("pdf_corpus.execution_settings_custom") }}</small>
    </summary>
    <fieldset class="execution-settings" :disabled="props.disabled">
      <p class="help" id="corpus-execution-help">
        {{ i18n.t("pdf_corpus.execution_settings_help") }}
      </p>
      <label class="defaults-toggle">
        <input
          type="checkbox"
          :checked="props.useProfileDefaults"
          @change="emit('update:useProfileDefaults', ($event.target as HTMLInputElement).checked)"
        />
        <span>{{ i18n.t("pdf_corpus.use_profile_defaults") }}</span>
      </label>

      <div class="settings-grid">
        <label class="field" for="corpus-num-ctx"
          ><span>{{ i18n.t("pdf_corpus.context_window") }}</span
          ><input
            id="corpus-num-ctx"
            class="control"
            type="number"
            min="2048"
            step="1024"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.num_ctx ?? ''"
            @input="numericGeneration('num_ctx', $event, { integer: true, min: 2048 })"
          /><small>{{ i18n.t("pdf_corpus.context_window_help") }}</small></label
        >
        <label class="field" for="corpus-concurrency"
          ><span>{{ i18n.t("pdf_corpus.max_concurrent") }}</span
          ><input
            id="corpus-concurrency"
            class="control"
            type="number"
            min="1"
            max="16"
            :value="props.maxConcurrentRequests"
            @input="concurrent"
          /><small>{{ i18n.t("pdf_corpus.max_concurrent_help") }}</small></label
        >
        <label class="field" for="corpus-temperature"
          ><span>{{ i18n.t("pdf_corpus.temperature") }}</span
          ><input
            id="corpus-temperature"
            class="control"
            type="number"
            min="0"
            max="2"
            step="0.05"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.temperature ?? ''"
            @input="numericGeneration('temperature', $event)"
        /></label>
        <label class="field" for="corpus-top-k"
          ><span>{{ i18n.t("pdf_corpus.top_k") }}</span
          ><input
            id="corpus-top-k"
            class="control"
            type="number"
            min="0"
            step="1"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.top_k ?? ''"
            @input="numericGeneration('top_k', $event, { integer: true, min: 0 })"
        /></label>
        <label class="field" for="corpus-top-p"
          ><span>{{ i18n.t("pdf_corpus.top_p") }}</span
          ><input
            id="corpus-top-p"
            class="control"
            type="number"
            min="0"
            max="1"
            step="0.01"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.top_p ?? ''"
            @input="numericGeneration('top_p', $event)"
        /></label>
        <label class="field" for="corpus-min-p"
          ><span>{{ i18n.t("pdf_corpus.min_p") }}</span
          ><input
            id="corpus-min-p"
            class="control"
            type="number"
            min="0"
            max="1"
            step="0.01"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.min_p ?? ''"
            @input="numericGeneration('min_p', $event)"
        /></label>
        <label class="field" for="corpus-repeat"
          ><span>{{ i18n.t("pdf_corpus.repeat_penalty") }}</span
          ><input
            id="corpus-repeat"
            class="control"
            type="number"
            min="0"
            step="0.05"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.repeat_penalty ?? ''"
            @input="numericGeneration('repeat_penalty', $event)"
        /></label>
        <label class="field" for="corpus-seed"
          ><span>{{ i18n.t("pdf_corpus.seed") }}</span
          ><input
            id="corpus-seed"
            class="control"
            type="number"
            step="1"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.seed ?? ''"
            @input="numericGeneration('seed', $event, { integer: true })"
        /></label>
        <label class="field" for="corpus-think"
          ><span>{{ i18n.t("pdf_corpus.thinking") }}</span
          ><select
            id="corpus-think"
            class="control"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="String(props.generation?.think ?? 'false')"
            @change="thinkingGeneration($event)"
          >
            <option value="false">{{ i18n.t("pdf_corpus.thinking_off") }}</option>
            <option value="true">{{ i18n.t("pdf_corpus.thinking_on") }}</option>
            <option value="low">{{ i18n.t("pdf_corpus.thinking_low") }}</option>
            <option value="medium">{{ i18n.t("pdf_corpus.thinking_medium") }}</option>
            <option value="high">{{ i18n.t("pdf_corpus.thinking_high") }}</option>
          </select></label
        >
        <label class="field" for="corpus-mirostat"
          ><span>{{ i18n.t("pdf_corpus.mirostat") }}</span
          ><select
            id="corpus-mirostat"
            class="control"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="String(props.generation?.mirostat ?? 0)"
            @change="numericGeneration('mirostat', $event, { integer: true, min: 0 })"
          >
            <option value="0">{{ i18n.t("pdf_corpus.mirostat_off") }}</option>
            <option value="1">Mirostat 1</option>
            <option value="2">Mirostat 2</option>
          </select></label
        >
        <label class="field" for="corpus-mirostat-eta"
          ><span>{{ i18n.t("pdf_corpus.mirostat_eta") }}</span
          ><input
            id="corpus-mirostat-eta"
            class="control"
            type="number"
            min="0"
            step="0.01"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.mirostat_eta ?? ''"
            @input="numericGeneration('mirostat_eta', $event, { min: 0 })"
        /></label>
        <label class="field" for="corpus-mirostat-tau"
          ><span>{{ i18n.t("pdf_corpus.mirostat_tau") }}</span
          ><input
            id="corpus-mirostat-tau"
            class="control"
            type="number"
            min="0"
            step="0.1"
            :disabled="props.disabled || props.useProfileDefaults"
            :value="props.generation?.mirostat_tau ?? ''"
            @input="numericGeneration('mirostat_tau', $event, { min: 0 })"
        /></label>
      </div>

      <details class="stage-budgets">
        <summary>{{ i18n.t("pdf_corpus.stage_budgets") }}</summary>
        <p class="help">{{ i18n.t("pdf_corpus.stage_budgets_help") }}</p>
        <div class="settings-grid stage-grid">
          <label class="field" for="corpus-window"
            ><span>{{ i18n.t("pdf_corpus.segmentation_window") }}</span
            ><input
              id="corpus-window"
              class="control"
              type="number"
              min="1024"
              max="24000"
              step="256"
              :value="
                props.stageLimits?.segmentation_window_tokens ?? defaults.segmentation_window_tokens
              "
              @input="stage('segmentation_window_tokens', $event)"
            /><small>{{ i18n.t("pdf_corpus.segmentation_window_help") }}</small></label
          >
          <label class="field" for="corpus-seg-output"
            ><span>{{ i18n.t("pdf_corpus.segmentation_output") }}</span
            ><input
              id="corpus-seg-output"
              class="control"
              type="number"
              min="256"
              max="8192"
              step="128"
              :value="
                props.stageLimits?.segmentation_num_predict ?? defaults.segmentation_num_predict
              "
              @input="stage('segmentation_num_predict', $event)"
          /></label>
          <label class="field" for="corpus-reconcile-output"
            ><span>{{ i18n.t("pdf_corpus.reconciliation_output") }}</span
            ><input
              id="corpus-reconcile-output"
              class="control"
              type="number"
              min="256"
              max="8192"
              step="128"
              :value="
                props.stageLimits?.reconciliation_num_predict ?? defaults.reconciliation_num_predict
              "
              @input="stage('reconciliation_num_predict', $event)"
          /></label>
          <label class="field" for="corpus-manifest-output"
            ><span>{{ i18n.t("pdf_corpus.manifest_output") }}</span
            ><input
              id="corpus-manifest-output"
              class="control"
              type="number"
              min="256"
              max="8192"
              step="128"
              :value="props.stageLimits?.manifest_num_predict ?? defaults.manifest_num_predict"
              @input="stage('manifest_num_predict', $event)"
          /></label>
          <label class="field" for="corpus-discourse-output"
            ><span>{{ i18n.t("pdf_corpus.discourse_output") }}</span
            ><input
              id="corpus-discourse-output"
              class="control"
              type="number"
              min="256"
              max="8192"
              step="128"
              :value="props.stageLimits?.discourse_num_predict ?? defaults.discourse_num_predict"
              @input="stage('discourse_num_predict', $event)"
          /></label>
          <label class="field" for="corpus-quotation-output"
            ><span>{{ i18n.t("pdf_corpus.quotation_output") }}</span
            ><input
              id="corpus-quotation-output"
              class="control"
              type="number"
              min="256"
              max="8192"
              step="128"
              :value="props.stageLimits?.quotation_num_predict ?? defaults.quotation_num_predict"
              @input="stage('quotation_num_predict', $event)"
          /></label>
          <label class="field" for="corpus-index-output"
            ><span>{{ i18n.t("pdf_corpus.indexing_output") }}</span
            ><input
              id="corpus-index-output"
              class="control"
              type="number"
              min="256"
              max="8192"
              step="128"
              :value="props.stageLimits?.indexing_num_predict ?? defaults.indexing_num_predict"
              @input="stage('indexing_num_predict', $event)"
          /></label>
        </div>
      </details>

      <details class="stage-budgets">
        <summary>{{ i18n.t("pdf_corpus.stage_timeouts") }}</summary>
        <p class="help">{{ i18n.t("pdf_corpus.stage_timeouts_help") }}</p>
        <div class="settings-grid stage-grid">
          <label
            v-for="key in [
              'manifest',
              'segmentation',
              'reconciliation',
              'discourse',
              'quotation',
              'indexing',
            ]"
            :key="key"
            class="field"
            :for="`corpus-timeout-${key}`"
            ><span
              >{{ i18n.t(`pdf_corpus.timeout.${key}`, key) }} ·
              {{ i18n.t("pdf_corpus.seconds") }}</span
            ><input
              :id="`corpus-timeout-${key}`"
              class="control"
              type="number"
              min="30"
              max="1800"
              step="30"
              :value="
                props.stageTimeouts?.[key] ?? timeoutDefaults[key as keyof typeof timeoutDefaults]
              "
              @input="stageTimeout(key, $event)"
          /></label>
        </div>
      </details>

      <div
        class="context-check"
        :class="{ unsafe: !contextSafe }"
        :role="contextSafe ? 'status' : 'alert'"
      >
        <b>{{
          contextSafe ? i18n.t("pdf_corpus.context_safe") : i18n.t("pdf_corpus.context_unsafe")
        }}</b>
        <span v-if="numCtx">{{
          i18n.tf("pdf_corpus.context_budget_detail", {
            required: requiredContext.toLocaleString(),
            context: numCtx.toLocaleString(),
          })
        }}</span>
        <span v-else>{{ i18n.t("pdf_corpus.context_unknown") }}</span>
      </div>
    </fieldset>
  </details>
</template>

<style scoped>
.execution-settings-shell {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.execution-settings-summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.execution-settings-summary small {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--muted);
}
.execution-settings {
  border: 0;
  border-top: 1px solid var(--line);
  padding: 10px 12px;
  min-inline-size: 0;
  display: grid;
  gap: 10px;
}
.execution-settings > legend {
  font-size: 0.8125rem;
  font-weight: 800;
  padding-inline: 4px;
}
.help,
.field small {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.4;
}
.help {
  margin: 0;
}
.defaults-toggle {
  display: flex;
  gap: 7px;
  align-items: center;
  font-size: 0.8125rem;
  font-weight: 700;
}
.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(150px, 1fr));
  gap: 9px;
}
.field {
  display: grid;
  gap: 4px;
  align-content: start;
  font-size: 0.8125rem;
  font-weight: 700;
}
.field small {
  font-weight: 400;
}
.stage-budgets {
  border-top: 1px solid var(--line);
  padding-top: 8px;
}
.stage-budgets summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.stage-grid {
  margin-top: 8px;
}
.context-check {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--tone-ok-bg);
  font-size: 0.8125rem;
}
.context-check.unsafe {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.context-check span {
  color: inherit;
}
.control:focus-visible,
summary:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 600px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import PipelineTypeChip from "./PipelineTypeChip.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { choiceFromKey, optionKey, type BindingChoice } from "../../domain/pipelineBindings";
import { sourceText } from "../../domain/pipelineAnalysisPresentation";
import { pipelineDataTypeLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineStage,
  PipelineStageWiring,
  PipelineWiringInput,
  PipelineWiringOption,
} from "../../types/pipelines";

const props = defineProps<{
  stage: PipelineStage;
  /** The server's resolved wiring for this stage; null until an analysis arrives. */
  wiring: PipelineStageWiring | null;
  loading?: boolean;
  error?: string;
}>();
const emit = defineEmits<{ bind: [port: string, choice: BindingChoice | null] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const uid = computed(() => `ports-${props.stage.id.replace(/[^a-z0-9_-]/gi, "_")}`);

const statusTone = {
  bound: "success",
  unbound: "danger",
  optional_unbound: "neutral",
  mismatch: "danger",
} as const;

function statusLabel(row: PipelineWiringInput) {
  const labels = {
    bound: t("pipelines.ports_status_bound", "Connected"),
    unbound: t("pipelines.ports_status_unbound", "Not connected"),
    optional_unbound: t("pipelines.ports_status_optional_unbound", "Not connected (optional)"),
    mismatch: t("pipelines.ports_status_mismatch", "Wrong type"),
  };
  return labels[row.status];
}

function typeName(type: string) {
  return pipelineDataTypeLabel(type, t);
}

function optionLabel(option: PipelineWiringOption) {
  return option.kind === "run_input"
    ? i18n.tf("pipelines.ports_option_run", "Workflow input “{name}” ({type})", {
        name: option.name ?? "",
        type: typeName(option.data_type),
      })
    : i18n.tf("pipelines.ports_option_stage", "{stage} → {output} ({type})", {
        stage: option.stage ?? "",
        output: option.output ?? "",
        type: typeName(option.data_type),
      });
}

function groups(row: PipelineWiringInput) {
  const upstream = row.options.filter((item) => item.kind === "stage" && item.upstream);
  const connect = row.options.filter((item) => item.kind === "stage" && !item.upstream);
  const runInputs = row.options.filter((item) => item.kind === "run_input");
  return [
    {
      id: "upstream",
      label: t("pipelines.ports_group_upstream", "Earlier stages"),
      items: upstream,
    },
    {
      id: "connect",
      label: t("pipelines.ports_group_connect", "Other stages (adds a connection)"),
      items: connect,
    },
    {
      id: "run",
      label: t("pipelines.ports_group_run", "Inputs the workflow supplies"),
      items: runInputs,
    },
  ].filter((group) => group.items.length);
}

function selected(row: PipelineWiringInput) {
  const explicit = row.explicit ? row.sources[0] : null;
  return explicit ? optionKey(explicit) : "";
}

/** The fixed number currently bound to a tuning port, or null. */
function constantValue(row: PipelineWiringInput): number | null {
  const source = row.explicit ? row.sources[0] : null;
  return source?.kind === "constant" && typeof source.value === "number" ? source.value : null;
}

function constantRange(row: PipelineWiringInput) {
  return i18n.tf("pipelines.ports_constant_range", "Between {min} and {max}.", {
    min: String(row.minimum ?? "−∞"),
    max: String(row.maximum ?? "∞"),
  });
}

function setConstant(row: PipelineWiringInput, raw: string) {
  const value = Number(raw);
  if (raw.trim() === "" || !Number.isFinite(value)) return;
  emit("bind", row.port, { kind: "constant", value });
}

function describeSources(row: PipelineWiringInput) {
  if (!row.sources.length) return t("pipelines.ports_none", "Nothing is connected.");
  return i18n.tf("pipelines.ports_currently", "Currently: {source}", {
    source: row.sources.map((source) => sourceText(source, t)).join(", "),
  });
}

function choose(row: PipelineWiringInput, key: string) {
  if (!key) return emit("bind", row.port, null);
  if (key === "constant") {
    return emit("bind", row.port, {
      kind: "constant",
      value: constantValue(row) ?? row.minimum ?? 0,
    });
  }
  const found = choiceFromKey(key, row.options);
  if (found) emit("bind", row.port, found.choice);
}

const hasExplicit = computed(() => props.wiring?.inputs.some((row) => row.explicit) ?? false);
</script>

<template>
  <section class="ports" :aria-labelledby="`${uid}-heading`">
    <h5 :id="`${uid}-heading`" class="label-with-help">
      {{ t("pipelines.ports_heading", "Inputs and outputs") }}
      <UiTooltip
        :text="
          t(
            'pipelines.ports_help',
            'A stage only accepts the type each input declares. Choose where each input comes from: the output of an earlier stage, or a value the workflow supplies on every run.',
          )
        "
      />
    </h5>

    <p v-if="!wiring && loading" class="ports-note" role="status">
      {{ t("pipelines.ports_loading", "Checking inputs…") }}
    </p>
    <p v-else-if="!wiring && error" class="ports-note" data-tone="danger" role="alert">
      {{
        i18n.tf("pipelines.ports_unavailable", "Input checking is unavailable: {message}", {
          message: error,
        })
      }}
    </p>

    <template v-if="wiring">
      <h6 class="ports-subhead">{{ t("pipelines.ports_inputs", "Inputs") }}</h6>
      <ul class="port-list">
        <li v-for="row in wiring.inputs" :key="row.port" class="port" :data-status="row.status">
          <div class="port-head">
            <code class="port-name">{{ row.port }}</code>
            <PipelineTypeChip :type="row.data_type" />
            <span class="port-meta">
              {{
                row.required
                  ? t("pipelines.ports_required", "Required")
                  : t("pipelines.ports_optional", "Optional")
              }}
              <template v-if="row.multiple">
                · {{ t("pipelines.ports_merges", "merges several sources") }}
              </template>
            </span>
            <UiStatusBadge :label="statusLabel(row)" :tone="statusTone[row.status]" />
          </div>
          <label class="port-source">
            <span>{{ t("pipelines.ports_source", "Source") }}</span>
            <select
              class="control"
              :value="selected(row)"
              :aria-describedby="`${uid}-${row.port}-now`"
              @change="choose(row, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">
                {{ t("pipelines.ports_automatic", "Automatic — from this stage’s connections") }}
              </option>
              <optgroup v-for="group in groups(row)" :key="group.id" :label="group.label">
                <option
                  v-for="option in group.items"
                  :key="optionKey(option)"
                  :value="optionKey(option)"
                  :disabled="!option.possible"
                >
                  {{ optionLabel(option) }}
                </option>
              </optgroup>
              <optgroup
                v-if="row.accepts_constant"
                :label="t('pipelines.ports_group_constant', 'Fixed value')"
              >
                <option value="constant">
                  {{ t("pipelines.ports_option_constant", "A fixed number") }}
                </option>
              </optgroup>
            </select>
          </label>
          <label v-if="row.accepts_constant && constantValue(row) !== null" class="port-source">
            <span>{{ t("pipelines.ports_constant_value", "Value") }}</span>
            <input
              class="control"
              type="number"
              inputmode="decimal"
              :min="row.minimum ?? undefined"
              :max="row.maximum ?? undefined"
              :value="constantValue(row) ?? ''"
              :aria-describedby="`${uid}-${row.port}-range`"
              @change="setConstant(row, ($event.target as HTMLInputElement).value)"
            />
            <small :id="`${uid}-${row.port}-range`" class="port-now">{{
              constantRange(row)
            }}</small>
          </label>
          <small :id="`${uid}-${row.port}-now`" class="port-now">{{ describeSources(row) }}</small>
        </li>
      </ul>

      <h6 class="ports-subhead">{{ t("pipelines.ports_outputs", "Outputs") }}</h6>
      <ul class="port-list">
        <li v-for="out in wiring.outputs" :key="out.name" class="port">
          <div class="port-head">
            <code class="port-name">{{ out.name }}</code>
            <PipelineTypeChip :type="out.data_type" />
          </div>
          <small class="port-now">
            {{
              out.consumers.length
                ? i18n.tf("pipelines.ports_used_by", "Used by {consumers}", {
                    consumers: out.consumers.map((c) => `${c.stage}.${c.port}`).join(", "),
                  })
                : t("pipelines.ports_unused", "Not used by any stage.")
            }}
          </small>
        </li>
      </ul>

      <p v-if="hasExplicit" class="ports-note" role="note">
        {{
          t(
            "pipelines.ports_explicit_note",
            "Inputs set explicitly differ from the connections. Runtime adapters take inputs from the connections, so a pipeline that rewires inputs can be saved and inspected but not made active.",
          )
        }}
      </p>
    </template>
  </section>
</template>

<style scoped>
.ports {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.ports h5 {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.9375rem;
}
.ports-subhead {
  margin: var(--space-1) 0 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.port-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.port {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.port[data-status="unbound"],
.port[data-status="mismatch"] {
  border-color: var(--tone-danger-edge);
  background: var(--tone-danger-bg);
}
.port-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.port-name {
  color: var(--text-primary);
  font-weight: 800;
}
.port-meta {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.port-source {
  display: grid;
  gap: 2px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 700;
}
.port-now {
  color: var(--text-secondary);
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}
.ports-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.ports-note[data-tone="danger"] {
  color: var(--tone-danger-fg);
}
</style>

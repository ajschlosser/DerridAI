<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import PipelineTypeChip from "./PipelineTypeChip.vue";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import {
  primaryInput,
  primaryOutput,
  strategyFit,
  type InsertMode,
} from "../../domain/pipelineBindings";
import { formatMs } from "../../domain/pipelineAnalysisPresentation";
import {
  pipelineDataTypeLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { findTerm, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelinePurpose,
  PipelineStage,
  PipelineStrategy,
  PipelineStrategyLatency,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  strategies: PipelineStrategy[];
  purpose: PipelinePurpose | null;
  vocabulary?: PipelineWorkflowVocabulary;
  /** The selected stage the new one is placed relative to. */
  anchor: PipelineStage | null;
  anchorStrategy: PipelineStrategy | null;
  /** Observed per-strategy latency, to show what a stage typically costs. */
  latency?: Record<string, PipelineStrategyLatency> | null;
}>();
const emit = defineEmits<{ close: []; add: [strategyId: string, mode: InsertMode] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const query = ref("");
const onlyFits = ref(true);
const showInspectOnly = ref(false);
const hasFollowers = computed(() => (props.anchor?.next.length ?? 0) > 0);
const mode = ref<InsertMode>(props.anchor ? "after" : "entry");
watch(
  () => props.anchor?.id,
  () => {
    mode.value = props.anchor ? "after" : "entry";
  },
);
const runInputs = computed(() => props.purpose?.run_inputs ?? []);
const producer = computed(() => (mode.value === "entry" ? null : props.anchorStrategy));

type Row = {
  strategy: PipelineStrategy;
  fits: boolean;
  needs: string;
  provides: string;
  inspectOnly: boolean;
  reason: string;
};

function describeMiss(strategy: PipelineStrategy): { reason: string; needs: string } {
  const fit = strategyFit(strategy, producer.value, runInputs.value);
  if (fit.fits) return { reason: "", needs: "" };
  if (fit.reason === "missing_input") {
    return {
      reason: i18n.tf(
        "pipelines.palette_missing_input",
        "Needs a workflow input named “{name}”, which this workflow does not supply.",
        { name: fit.needs ?? "" },
      ),
      needs: fit.needs ?? "",
    };
  }
  return {
    reason: producer.value
      ? i18n.tf(
          "pipelines.palette_type_mismatch",
          "Takes {needs}, but {stage} provides {provides}.",
          {
            needs: pipelineDataTypeLabel(fit.needs ?? "", t),
            stage: props.anchor?.id ?? "",
            provides: pipelineDataTypeLabel(fit.provides ?? "", t),
          },
        )
      : i18n.tf(
          "pipelines.palette_not_a_start",
          "Takes {needs}, which this workflow does not supply to a starting stage.",
          { needs: pipelineDataTypeLabel(fit.needs ?? "", t) },
        ),
    needs: fit.needs ?? "",
  };
}

const rows = computed<Row[]>(() =>
  props.strategies
    .map((strategy) => {
      const fit = strategyFit(strategy, producer.value, runInputs.value);
      const supported = props.purpose
        ? (props.purpose.strategy_fit[strategy.strategy_id] ?? "inspect_only")
        : "supported";
      const miss = describeMiss(strategy);
      return {
        strategy,
        fits: fit.fits,
        needs: primaryInput(strategy).data_type,
        provides: primaryOutput(strategy).data_type,
        inspectOnly: supported === "inspect_only",
        reason: miss.reason,
        supported,
      };
    })
    // A strategy that would change what the workflow returns can never run in it.
    .filter((row) => row.supported !== "output_contract"),
);

const visible = computed(() => {
  const needle = query.value.trim().toLowerCase();
  return rows.value.filter((row) => {
    if (onlyFits.value && !row.fits) return false;
    if (!showInspectOnly.value && row.inspectOnly) return false;
    if (!needle) return true;
    const haystack = [
      row.strategy.strategy_id,
      pipelineStrategyLabel(row.strategy, t),
      pipelineStrategyDescription(row.strategy, t),
      pipelineStageFamilyLabel(row.strategy.family, t),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });
});

const groups = computed(() => {
  const order = (props.vocabulary?.phases ?? []).map((term) => term.id);
  const byPhase = new Map<string, Row[]>();
  for (const row of visible.value) {
    const list = byPhase.get(row.strategy.phase) ?? [];
    list.push(row);
    byPhase.set(row.strategy.phase, list);
  }
  return [...byPhase.entries()]
    .sort(([a], [b]) => order.indexOf(a) - order.indexOf(b))
    .map(([phase, items]) => {
      const term = findTerm(props.vocabulary?.phases, phase);
      return {
        id: phase,
        label: term ? termLabel(term, t) : phase,
        rows: [...items].sort((a, b) =>
          pipelineStrategyLabel(a.strategy, t).localeCompare(
            pipelineStrategyLabel(b.strategy, t),
            i18n.locale,
          ),
        ),
      };
    });
});

const hiddenByFit = computed(
  () => rows.value.filter((row) => !row.fits && (showInspectOnly.value || !row.inspectOnly)).length,
);

function typical(strategyId: string) {
  const figure = props.latency?.[strategyId];
  return figure && figure.samples ? formatMs(figure.p50_ms, t) : "";
}
</script>

<template>
  <UiDialog
    :title="t('pipelines.palette_title', 'Add a stage')"
    :description="
      t(
        'pipelines.palette_description',
        'Each stage declares what it takes and what it gives. Only stages that can receive what the chosen position provides are offered.',
      )
    "
    :close-label="t('common.close', 'Close')"
    size="xlarge"
    @close="emit('close')"
  >
    <div class="palette">
      <fieldset class="palette-where">
        <legend>{{ t("pipelines.palette_where", "Where it goes") }}</legend>
        <label v-if="anchor">
          <input v-model="mode" type="radio" value="after" name="palette-mode" />
          {{
            i18n.tf("pipelines.palette_after", "As a next step after {stage}", {
              stage: anchor.id,
            })
          }}
        </label>
        <label v-if="anchor && hasFollowers">
          <input v-model="mode" type="radio" value="between" name="palette-mode" />
          {{
            i18n.tf("pipelines.palette_between", "Between {stage} and the stages that follow it", {
              stage: anchor.id,
            })
          }}
        </label>
        <label>
          <input v-model="mode" type="radio" value="entry" name="palette-mode" />
          {{ t("pipelines.palette_entry", "As a new starting point, fed by the workflow") }}
        </label>
      </fieldset>

      <div class="palette-filters">
        <label class="palette-search">
          <span>{{ t("pipelines.palette_search", "Search stages") }}</span>
          <input v-model="query" class="control" type="search" autocomplete="off" />
        </label>
        <label class="palette-check">
          <input v-model="onlyFits" type="checkbox" />
          {{ t("pipelines.palette_only_fits", "Only stages that fit this position") }}
        </label>
        <label class="palette-check">
          <input v-model="showInspectOnly" type="checkbox" />
          {{ t("pipelines.palette_show_inspect_only", "Include stages this workflow cannot run") }}
        </label>
      </div>
      <p v-if="onlyFits && hiddenByFit" class="palette-note" role="status">
        {{
          i18n.tf(
            "pipelines.palette_hidden",
            "{count} more stages are hidden because they cannot receive what this position provides.",
            { count: hiddenByFit },
          )
        }}
      </p>

      <p v-if="!groups.length" class="palette-empty" role="status">
        {{ t("pipelines.palette_empty", "No stage matches. Clear the search or the fit filter.") }}
      </p>

      <section v-for="group in groups" :key="group.id" class="palette-group">
        <h4>{{ group.label }}</h4>
        <ul>
          <li v-for="row in group.rows" :key="row.strategy.strategy_id" :data-fits="row.fits">
            <div class="row-main">
              <strong>{{ pipelineStrategyLabel(row.strategy, t) }}</strong>
              <span class="row-io">
                <span class="row-io-label">{{ t("pipelines.palette_takes", "Takes") }}</span>
                <PipelineTypeChip :type="row.needs" />
                <span aria-hidden="true">→</span>
                <span class="row-io-label">{{ t("pipelines.palette_gives", "Gives") }}</span>
                <PipelineTypeChip :type="row.provides" />
              </span>
              <p class="row-description">{{ pipelineStrategyDescription(row.strategy, t) }}</p>
              <span class="row-cost">
                <code v-if="row.strategy.complexity">{{ row.strategy.complexity.time }}</code>
                <UiStatusBadge
                  v-if="row.strategy.invokes_llm"
                  :label="t('pipelines.palette_model_call', 'Calls a language model')"
                  tone="warning"
                />
                <span v-if="typical(row.strategy.strategy_id)" class="row-typical">
                  {{
                    i18n.tf("pipelines.palette_typical", "typically {time}", {
                      time: typical(row.strategy.strategy_id),
                    })
                  }}
                </span>
                <UiStatusBadge
                  v-if="row.inspectOnly"
                  :label="t('pipelines.palette_inspect_only', 'Inspect only')"
                  tone="neutral"
                />
              </span>
              <small v-if="!row.fits" class="row-reason">{{ row.reason }}</small>
            </div>
            <UiButton
              size="small"
              :button-class="'palette-add'"
              @click="emit('add', row.strategy.strategy_id, mode)"
            >
              {{ t("pipelines.palette_add", "Add") }}
              <span class="visually-hidden">{{ pipelineStrategyLabel(row.strategy, t) }}</span>
            </UiButton>
          </li>
        </ul>
      </section>
    </div>
    <template #footer>
      <UiButton :label="t('common.cancel', 'Cancel')" @click="emit('close')" />
    </template>
  </UiDialog>
</template>

<style scoped>
.palette {
  display: grid;
  gap: var(--space-3);
}
.palette-where {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}
.palette-where legend {
  padding: 0 var(--space-1);
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.palette-where label,
.palette-check {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-primary);
  font-size: 0.875rem;
}
.palette-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: var(--space-3);
}
.palette-search {
  display: grid;
  gap: 2px;
  flex: 1 1 240px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 700;
}
.palette-note,
.palette-empty {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.palette-group {
  display: grid;
  gap: var(--space-1);
}
.palette-group h4 {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.palette-group ul {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.palette-group li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.palette-group li[data-fits="false"] {
  background: var(--surface-inset);
}
.row-main {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}
.row-io {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
}
.row-io-label {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.row-description {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.row-cost {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.row-cost code {
  color: var(--text-primary);
  font-size: 0.8125rem;
}
.row-typical {
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.row-reason {
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
</style>

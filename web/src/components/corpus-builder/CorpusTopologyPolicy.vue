<script setup lang="ts">
import { computed } from "vue";
import type { CorpusTopologyPolicy } from "../../types/corpus";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    modelValue: CorpusTopologyPolicy;
    syntheticPagesAvailable?: boolean;
    disabled?: boolean;
  }>(),
  { syntheticPagesAvailable: false, disabled: false },
);
const emit = defineEmits<{ "update:modelValue": [value: CorpusTopologyPolicy] }>();
const i18n = useI18nStore();

const fixed = computed(() => props.modelValue.mode === "source_units");
const syntheticPages = computed(() => props.modelValue.records_per_page != null);

function commit(changes: Partial<CorpusTopologyPolicy>) {
  const next: CorpusTopologyPolicy = {
    ...props.modelValue,
    ...changes,
  };
  next.source_units_per_record = Math.max(
    1,
    Math.min(100, Number(next.source_units_per_record || 1)),
  );
  next.records_per_page =
    next.records_per_page == null
      ? null
      : Math.max(1, Math.min(100, Number(next.records_per_page || 1)));
  emit("update:modelValue", next);
}
function setMode(mode: CorpusTopologyPolicy["mode"]) {
  commit({ mode });
}
function setUnits(value: string) {
  commit({ source_units_per_record: Number(value) });
}
function setPageGrouping(enabled: boolean) {
  commit({ records_per_page: enabled ? props.modelValue.records_per_page || 1 : null });
}
function setRecordsPerPage(value: string) {
  commit({ records_per_page: Number(value) });
}
const relationshipSummary = computed(() => {
  if (!fixed.value) {
    return i18n.t(
      "pdf_corpus.topology.semantic_summary",
      "Semantic boundaries determine Records; SourceUnits remain the evidence floor.",
    );
  }
  const units = props.modelValue.source_units_per_record;
  const recordPart =
    units === 1 ? "1 SourceUnit → 1 Record" : `${units} SourceUnits → 1 Record`;
  if (!props.syntheticPagesAvailable || props.modelValue.records_per_page == null) return recordPart;
  const pages = props.modelValue.records_per_page;
  return `${recordPart} → ${pages} ${pages === 1 ? "Record" : "Records"} per synthetic Page`;
});
</script>

<template>
  <section class="topology-policy" aria-labelledby="corpus-topology-policy-title">
    <header>
      <div>
        <h4 id="corpus-topology-policy-title">
          {{ i18n.t("pdf_corpus.topology.title", "SourceUnit → Record → Page") }}
        </h4>
        <p>
          {{
            i18n.t(
              "pdf_corpus.topology.help",
              "Choose whether Record boundaries are inferred semantically or follow the SourceUnit structure exactly.",
            )
          }}
        </p>
      </div>
      <strong class="topology-summary">{{ relationshipSummary }}</strong>
    </header>

    <fieldset class="topology-modes" :disabled="disabled">
      <legend class="sr-only">
        {{ i18n.t("pdf_corpus.topology.record_rule", "Record boundary rule") }}
      </legend>
      <label :class="{ selected: !fixed }">
        <input
          type="radio"
          name="corpus-topology-mode"
          value="semantic"
          :checked="modelValue.mode === 'semantic'"
          @change="setMode('semantic')"
        />
        <span>
          <b>{{ i18n.t("pdf_corpus.topology.semantic", "Semantic Records") }}</b>
          <small>
            {{
              i18n.t(
                "pdf_corpus.topology.semantic_help",
                "Use discourse and structure to propose Record boundaries, then apply the Record-size safety policy.",
              )
            }}
          </small>
        </span>
      </label>
      <label :class="{ selected: fixed }">
        <input
          type="radio"
          name="corpus-topology-mode"
          value="source_units"
          :checked="modelValue.mode === 'source_units'"
          @change="setMode('source_units')"
        />
        <span>
          <b>{{ i18n.t("pdf_corpus.topology.fixed_units", "Fixed SourceUnit groups") }}</b>
          <small>
            {{
              i18n.t(
                "pdf_corpus.topology.fixed_units_help",
                "Construct Records deterministically from the SourceUnits you chose above.",
              )
            }}
          </small>
        </span>
      </label>
    </fieldset>

    <div v-if="fixed" class="topology-relation">
      <label for="corpus-source-units-per-record">
        <span>
          <b>{{ i18n.t("pdf_corpus.topology.units_per_record", "SourceUnits per Record") }}</b>
          <small>
            {{
              i18n.t(
                "pdf_corpus.topology.units_per_record_help",
                "Use 1 when each SourceUnit should become exactly one Record.",
              )
            }}
          </small>
        </span>
        <input
          id="corpus-source-units-per-record"
          class="control"
          type="number"
          min="1"
          max="100"
          step="1"
          :value="modelValue.source_units_per_record"
          :disabled="disabled"
          @change="setUnits(($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>

    <div v-if="syntheticPagesAvailable" class="page-policy">
      <label class="page-toggle">
        <input
          type="checkbox"
          :checked="syntheticPages"
          :disabled="disabled"
          @change="setPageGrouping(($event.target as HTMLInputElement).checked)"
        />
        <span>
          <b>{{ i18n.t("pdf_corpus.topology.synthetic_pages", "Define Pages from Records") }}</b>
          <small>
            {{
              i18n.t(
                "pdf_corpus.topology.synthetic_pages_help",
                "For sources without authoritative pages, group the constructed Records into stable synthetic Pages.",
              )
            }}
          </small>
        </span>
      </label>
      <label v-if="syntheticPages" for="corpus-records-per-page" class="records-per-page">
        <span>{{ i18n.t("pdf_corpus.topology.records_per_page", "Records per Page") }}</span>
        <input
          id="corpus-records-per-page"
          class="control"
          type="number"
          min="1"
          max="100"
          step="1"
          :value="modelValue.records_per_page || 1"
          :disabled="disabled"
          @change="setRecordsPerPage(($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>
    <p v-else class="page-authority-note">
      {{
        i18n.t(
          "pdf_corpus.topology.source_pages_authoritative",
          "This source already has authoritative page structure, so Record grouping will not replace its page locators.",
        )
      }}
    </p>
  </section>
</template>

<style scoped>
.topology-policy {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.topology-policy header {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-5);
  align-items: flex-start;
  justify-content: space-between;
}
.topology-policy h4,
.topology-policy p {
  margin: 0;
}
.topology-policy header p {
  max-width: 72ch;
  margin-top: var(--space-1);
  color: var(--text-secondary);
  line-height: 1.45;
}
.topology-summary {
  max-width: 34rem;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
  font-size: var(--fs-sm);
}
.topology-modes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
}
.topology-modes label,
.page-toggle {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  cursor: pointer;
}
.topology-modes label.selected {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.topology-modes input,
.page-toggle input {
  margin-top: 0.2rem;
}
.topology-modes span,
.page-toggle span,
.topology-relation label > span {
  display: grid;
  gap: var(--space-1);
}
.topology-modes small,
.page-toggle small,
.topology-relation small {
  color: var(--text-secondary);
  line-height: 1.4;
}
.topology-relation,
.page-policy {
  display: grid;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.topology-relation label,
.records-per-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(6rem, 9rem);
  gap: var(--space-4);
  align-items: center;
}
.records-per-page > span {
  font-weight: var(--fw-semibold);
}
.page-authority-note {
  padding: var(--space-2) var(--space-3);
  border-inline-start: 3px solid var(--border-interactive);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
@media (max-width: 720px) {
  .topology-modes {
    grid-template-columns: 1fr;
  }
  .topology-relation label,
  .records-per-page {
    grid-template-columns: 1fr;
  }
}
</style>

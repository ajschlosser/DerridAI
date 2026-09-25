<script setup lang="ts">
import { computed } from "vue";
import { currentFieldAssertions } from "../../domain/fieldAssertions";
import { useI18nStore } from "../../stores/i18n";
import type {
  ResearchEvidenceSelection,
  ResearchFieldAssertionSummary,
  ResearchResultEvidence,
} from "../../types/research";

const props = withDefaults(
  defineProps<{
    selectedEvidence?: ResearchEvidenceSelection[];
    resultEvidence?: ResearchResultEvidence[];
    activeIndex?: number;
    canRemove?: boolean;
    researcher?: boolean;
  }>(),
  {
    selectedEvidence: () => [],
    resultEvidence: () => [],
    activeIndex: 0,
    canRemove: false,
    researcher: false,
  },
);
const emit = defineEmits<{ select: [index: number]; remove: [key: string]; clear: [] }>();
const i18n = useI18nStore();
const showingResult = computed(() => props.resultEvidence.length > 0);
const active = computed(() =>
  showingResult.value
    ? props.resultEvidence[
        Math.max(0, Math.min(props.activeIndex, props.resultEvidence.length - 1))
      ]
    : null,
);
const record = computed(() => active.value?.record || {});
function pageLabel(record: Record<string, unknown>) {
  const start = record.page_start ?? record.page ?? null,
    end = record.page_end ?? null;
  if (start == null) return "";
  return end != null && String(end) !== String(start) ? `${start}–${end}` : String(start);
}
function selectedPage(item: ResearchEvidenceSelection) {
  if (item.page_start == null) return "";
  return item.page_end != null && String(item.page_end) !== String(item.page_start)
    ? `${item.page_start}–${item.page_end}`
    : String(item.page_start);
}
function display(value: unknown) {
  if (Array.isArray(value)) return value.join(", ");
  if (value == null) return "";
  return String(value);
}
const HIDDEN_RESEARCH_METADATA = new Set(["region_type", "region_author", "primary_text"]);

function fieldLabel(field: string) {
  return i18n.t(
    `field.${field}`,
    field.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()),
  );
}

function assertionDisplayValue(assertion: ResearchFieldAssertionSummary) {
  if (assertion.value_status === "confirmed_absent") return i18n.t("ui.none");
  return display(assertion.value);
}

function rowsFromAssertions(assertions: ResearchFieldAssertionSummary[]) {
  return assertions
    .filter(
      (assertion) =>
        assertion.field_name &&
        !HIDDEN_RESEARCH_METADATA.has(assertion.field_name) &&
        (assertion.value_status === "confirmed_absent" || display(assertion.value)),
    )
    .map((assertion) => ({
      field: assertion.field_name,
      label: fieldLabel(assertion.field_name),
      value: assertionDisplayValue(assertion),
      assertion,
    }));
}

function fallbackRows(source: Record<string, unknown>) {
  const fields = [
    "speaker",
    "position_holder",
    "stance",
    "discourse_role",
    "proposition_status",
    "target",
    "quoted_speaker",
    "topics",
    "concepts",
  ];
  return fields
    .filter((field) => display(source[field]))
    .map((field) => ({
      field,
      label: fieldLabel(field),
      value: display(source[field]),
      assertion: null,
    }));
}

const relationRows = computed(() => {
  const canonical = rowsFromAssertions(
    currentFieldAssertions(record.value) as ResearchFieldAssertionSummary[],
  );
  return canonical.length ? canonical : fallbackRows(record.value);
});

function selectedRows(item: ResearchEvidenceSelection) {
  const canonical = rowsFromAssertions(item.assertions || []);
  if (canonical.length) return canonical;
  const metadata = item.metadata || {};
  const dynamic = Object.entries(metadata)
    .filter(([field, value]) => !HIDDEN_RESEARCH_METADATA.has(field) && display(value))
    .map(([field, value]) => ({
      field,
      label: fieldLabel(field),
      value: display(value),
      assertion: null,
    }));
  return dynamic.length ? dynamic : fallbackRows(item as Record<string, unknown>);
}
</script>

<template>
  <aside
    id="researchEvidencePanel"
    class="research-evidence-panel card"
    :aria-label="i18n.t('research.evidence_panel')"
  >
    <header class="research-panel-heading">
      <div>
        <b>{{
          showingResult
            ? i18n.t("research.answer_evidence")
            : i18n.t("rag.selected_evidence")
        }}</b
        ><small
          >{{ showingResult ? resultEvidence.length : selectedEvidence.length }}
          {{ i18n.t("research.records") }}</small
        >
      </div>
      <button
        v-if="!showingResult && selectedEvidence.length && canRemove"
        class="research-text-action"
        type="button"
        @click="emit('clear')"
      >
        {{ i18n.t("ui.clear") }}
      </button>
    </header>

    <template v-if="showingResult">
      <div
        class="research-evidence-index"
        role="list"
        :aria-label="i18n.t('research.evidence_list')"
      >
        <button
          v-for="(item, index) in resultEvidence"
          :key="item.evidence_id || index"
          type="button"
          role="listitem"
          :class="{ active: index === activeIndex }"
          @click="emit('select', index)"
        >
          <span class="research-evidence-tag">{{ item.evidence_id || `E${index}` }}</span>
          <span
            ><b>{{
              display(item.record?.work) ||
              display(item.record?.record_id) ||
              i18n.t("research.evidence")
            }}</b
            ><small
              ><template v-if="pageLabel(item.record || {})"
                >pp. {{ pageLabel(item.record || {}) }} · </template
              >{{ item.inline_citation || item.collection || "" }}</small
            ></span
          >
        </button>
      </div>
      <section v-if="active" class="research-evidence-inspector" aria-live="polite">
        <div class="research-evidence-inspector-head">
          <span class="research-evidence-tag large">{{
            active.evidence_id || `E${activeIndex}`
          }}</span>
          <div>
            <b>{{
              display(record.work) ||
              display(record.record_id) ||
              i18n.t("research.evidence")
            }}</b
            ><small>{{ active.inline_citation || "" }}</small>
          </div>
        </div>
        <dl v-if="relationRows.length" class="research-relation-grid">
          <template v-for="row in relationRows" :key="row.field"
            ><dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd></template
          >
        </dl>
        <p v-if="display(record.text)" class="research-evidence-text">{{ display(record.text) }}</p>
        <p v-else class="note">
          {{
            researcher
              ? i18n.t("research.researcher_evidence_summary")
              : i18n.t("research.no_evidence_text")
          }}
        </p>
        <div
          v-if="
            active.full_citation ||
            active.collection ||
            active.rerank_score != null ||
            display(record.topics) ||
            display(record.concepts)
          "
          class="research-evidence-metadata"
        >
          <span v-if="active.full_citation"
            ><b>{{ i18n.t("research.full_citation") }}</b
            >{{ active.full_citation }}</span
          >
          <span v-if="active.collection"
            ><b>{{ i18n.t("research.collection") }}</b
            >{{ active.collection }}</span
          >
          <span v-if="active.rerank_score != null"
            ><b>{{ i18n.t("research.rerank_score") }}</b
            >{{ Number(active.rerank_score).toFixed(3) }}</span
          >
          <span v-if="display(record.topics)"
            ><b>{{ i18n.t("research.topics") }}</b
            >{{ display(record.topics) }}</span
          >
          <span v-if="display(record.concepts)"
            ><b>{{ i18n.t("research.concepts") }}</b
            >{{ display(record.concepts) }}</span
          >
        </div>
      </section>
    </template>

    <template v-else>
      <div v-if="selectedEvidence.length" class="research-selected-list" role="list">
        <article v-for="item in selectedEvidence" :key="item.key" role="listitem">
          <details class="research-selected-details">
            <summary>
              <span
                ><b>{{ item.work || item.record_id || i18n.t("research.evidence") }}</b
                ><small
                  >{{ item.record_id
                  }}<template v-if="selectedPage(item)"> · pp. {{ selectedPage(item) }}</template
                  ><template v-if="item.inline_citation">
                    · {{ item.inline_citation }}</template
                  ></small
                ></span
              >
              <span aria-hidden="true" class="research-selected-chevron">⌄</span>
            </summary>
            <div class="research-selected-preview">
              <dl
                v-if="selectedRows(item).length"
                class="research-relation-grid compact"
              >
                <template v-for="row in selectedRows(item)" :key="row.field"
                  ><dt>{{ row.label }}</dt>
                  <dd>{{ row.value }}</dd></template
                >
              </dl>
              <p v-if="item.text_preview">
                {{ item.text_preview }}<template v-if="item.text_preview.length >= 280">…</template>
              </p>
              <p v-else class="note">
                {{
                  i18n.t("research.selected_preview_unavailable")
                }}
              </p>
            </div>
          </details>
          <button
            v-if="canRemove"
            type="button"
            :aria-label="`${i18n.t('ui.remove_evidence')}: ${item.record_id || item.work}`"
            @click="emit('remove', item.key)"
          >
            ×
          </button>
        </article>
      </div>
      <div v-else class="research-evidence-empty">
        <span aria-hidden="true">∴</span>
        <b>{{ i18n.t("research.no_selected_evidence") }}</b>
        <p>
          {{
            i18n.t("research.no_selected_evidence_help")
          }}
        </p>
      </div>
    </template>
  </aside>
</template>

<style scoped>
.research-evidence-inspector {
  overflow: auto;
  padding: 14px 15px 18px;
}
.research-evidence-inspector-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 9px;
  align-items: center;
  margin-bottom: 12px;
}
.research-evidence-inspector-head > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.research-evidence-inspector-head b {
  font-size: 0.8125rem;
}
.research-evidence-inspector-head small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.research-evidence-text {
  margin: 0;
  color: var(--text-2);
  font:
    13px/1.65 Georgia,
    "Times New Roman",
    serif;
  white-space: pre-line;
}
.research-evidence-metadata {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}
.research-evidence-metadata span {
  display: grid;
  gap: 2px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.research-evidence-metadata b {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.045em;
  color: var(--muted);
}
.research-selected-list {
  overflow: auto;
  display: grid;
  gap: 1px;
  padding: 7px;
}
.research-selected-list article {
  min-height: 52px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 34px;
  gap: 8px;
  align-items: center;
  padding: 7px 7px 7px 9px;
  border-radius: 8px;
}
.research-selected-list article:hover {
  background: var(--surface-raised);
}
.research-selected-list article > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.research-selected-list b {
  font-size: 0.8125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.research-selected-list small {
  font-size: 0.8125rem;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.research-selected-list article > button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 1.125rem;
  cursor: pointer;
}
.research-selected-list article > button:hover {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.research-selected-list article > button:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
}
.research-selected-list article {
  align-items: start;
}
.research-selected-details {
  min-width: 0;
}
.research-selected-details > summary {
  min-height: 38px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 18px;
  gap: 8px;
  align-items: center;
  cursor: pointer;
  list-style: none;
  border-radius: 7px;
  padding: 3px 4px;
}
.research-selected-details > summary::-webkit-details-marker {
  display: none;
}
.research-selected-details > summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.research-selected-details > summary > span:first-child {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.research-selected-chevron {
  justify-self: end;
  color: var(--muted);
  transition: transform 0.16s ease;
}
.research-selected-details[open] .research-selected-chevron {
  transform: rotate(180deg);
}
.research-selected-preview {
  display: grid;
  gap: 9px;
  padding: 8px 4px 5px;
}
.research-selected-preview > p {
  margin: 0;
  color: var(--text-2);
  font:
    12px/1.55 Georgia,
    "Times New Roman",
    serif;
}
.research-selected-list article > button {
  margin-top: 3px;
}
@media (prefers-reduced-motion: reduce) {
  .research-selected-chevron {
    transition: none;
  }
}
</style>

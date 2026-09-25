<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import RecordProvenance from "./RecordProvenance.vue";
import RecordIndexTerms from "./RecordIndexTerms.vue";
import RecordAnnotations from "./RecordAnnotations.vue";
import RecordPdfLinks from "./RecordPdfLinks.vue";
import RecordHistoryTimeline from "./RecordHistoryTimeline.vue";
import InspectorLayoutEditor from "./InspectorLayoutEditor.vue";
import type { RecordWorkspaceSnapshot } from "../../types/record";
import {
  loadInspectorLayout,
  saveInspectorLayout,
  defaultInspectorLayout,
  groupInspectorRows,
  type InspectorLayout,
  type InspectorLayoutRow,
} from "../../domain/inspectorLayout";

const props = defineProps<{ snapshot: RecordWorkspaceSnapshot }>();
const emit = defineEmits<{
  search: [field: string, value: string, contains?: boolean];
  change: [changes: Record<string, unknown>];
  addAnnotation: [];
  removeAnnotation: [id: string];
  openPdf: [index: number];
  removePdf: [index: number];
  removeAllPdf: [];
  pdfExplorer: [];
  linkCurrentPdf: [];
  openHistory: [];
}>();
const i18n = useI18nStore();
const tab = ref("overview");
const layout = ref<InspectorLayout>(loadInspectorLayout(props.snapshot.record || {}));
const layoutEditor = ref<{ open: () => void } | null>(null);
const record = computed(() => props.snapshot.record || {});
const tabs = computed(() => [
  ["overview", i18n.t("record.tab_overview")],
  ["provenance", i18n.t("record.tab_provenance")],
  ["indexing", i18n.t("record.tab_indexing")],
  ["pdf", i18n.t("record.tab_pdf")],
  ["annotations", i18n.t("record.tab_annotations")],
  ["history", i18n.t("record.tab_history")],
]);
const overviewSections = computed(() => groupInspectorRows(layout.value.overview));
const indexingFields = computed(() =>
  layout.value.indexing.filter((row): row is Extract<InspectorLayoutRow, { kind: "field" }> => row.kind === "field").map((row) => row.field),
);
const provenanceFields = computed(() =>
  layout.value.provenance.filter((row): row is Extract<InspectorLayoutRow, { kind: "field" }> => row.kind === "field").map((row) => row.field),
);
function applyLayout(next: InspectorLayout) {
  layout.value = next;
  saveInspectorLayout(next, record.value);
}
function resetLayout() {
  const next = defaultInspectorLayout(record.value);
  layout.value = next;
  saveInspectorLayout(next);
}
function headingText(label: string) {
  if (label === "Record context") return i18n.t("record.record_context");
  if (label === "Quotation provenance") return i18n.t("record.quotation_provenance");
  if (label === "Attribution") return i18n.t("record.attribution");
  if (label === "Discourse") return i18n.t("record.discourse");
  if (label === "Research index") return i18n.t("record.indexing_kicker");
  return label;
}
const pageSpan = computed(() => {
  const a = record.value.page_start ?? record.value.page;
  const b = record.value.page_end;
  if (a === null || a === undefined || a === "") return "—";
  return b !== null && b !== undefined && b !== "" && String(b) !== String(a)
    ? `${a}–${b}`
    : String(a);
});
function present(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "boolean")
    return value ? i18n.t("runtime.yes") : i18n.t("runtime.no");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function fieldLabel(key: string) {
  if (key === "__pages") return i18n.t("record.page");
  return i18n.t(
    `field.${key}`,
    key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()),
  );
}
function searchable(key: string, value: unknown) {
  return (
    value !== null &&
    value !== undefined &&
    String(value).trim() !== "" &&
    !["primary_text", "needs_review", "review_reason"].includes(key)
  );
}
function values(key: string) {
  const value = record.value[key];
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (value === null || value === undefined || value === "") return [];
  return [String(value)];
}
function tabId(key: string) {
  return `recordInspectorTab-${key}`;
}
function panelId(key: string) {
  return `recordInspectorPanel-${key}`;
}
async function activateTab(index: number) {
  const items = tabs.value;
  if (!items.length) return;
  const safe = ((index % items.length) + items.length) % items.length;
  tab.value = items[safe][0];
  await nextTick();
  const el = document.getElementById(tabId(tab.value));
  if (el instanceof HTMLButtonElement) el.focus();
}
function onTabKeydown(event: KeyboardEvent, index: number) {
  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    event.preventDefault();
    void activateTab(index + 1);
    return;
  }
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    event.preventDefault();
    void activateTab(index - 1);
    return;
  }
  if (event.key === "Home") {
    event.preventDefault();
    void activateTab(0);
    return;
  }
  if (event.key === "End") {
    event.preventDefault();
    void activateTab(tabs.value.length - 1);
  }
}
</script>
<template>
  <aside class="record-inspector" :aria-label="i18n.t('record.inspector')">
    <nav
      class="record-inspector-tabs"
      role="tablist"
      :aria-label="i18n.t('record.inspector_sections')"
    >
      <button
        v-for="(item, index) in tabs"
        :id="tabId(item[0])"
        :key="item[0]"
        type="button"
        role="tab"
        :aria-selected="tab === item[0]"
        :aria-controls="panelId(item[0])"
        :tabindex="tab === item[0] ? 0 : -1"
        :class="{ active: tab === item[0] }"
        @click="tab = item[0]"
        @keydown="onTabKeydown($event, index)"
      >
        {{ item[1]
        }}<span v-if="item[0] === 'annotations' && snapshot.annotations?.length">{{
          snapshot.annotations.length
        }}</span
        ><span v-if="item[0] === 'history' && snapshot.history_count">{{
          snapshot.history_count
        }}</span>
      </button>
    </nav>
    <div class="record-inspector-body">
      <section
        v-if="tab === 'overview'"
        :id="panelId('overview')"
        class="record-overview-panel"
        role="tabpanel"
        :aria-labelledby="tabId('overview')"
      >
        <div class="inspector-section-head">
          <p>{{ i18n.t("record.record_context") }}</p>
          <h2>{{ i18n.t("record.overview") }}</h2>
          <button type="button" class="btn tiny record-layout-button" @click="layoutEditor?.open()">
            {{ i18n.t("record.configure_fields") }}
          </button>
        </div>
        <section v-for="(section, index) in overviewSections" :key="`${section.heading || 'fields'}-${index}`" class="inspector-field-group">
          <h3 v-if="section.heading">{{ headingText(section.heading) }}</h3>
          <dl class="record-meta-list">
            <div v-for="field in section.fields" :key="field">
              <dt>{{ fieldLabel(field) }}</dt>
              <dd>
                <template v-if="field === '__pages'"
                  ><span class="record-page-value">{{ pageSpan }}</span></template
                ><button
                  v-else-if="searchable(field, record[field])"
                  type="button"
                  @click="emit('search', field, String(record[field]))"
                >
                  {{ present(record[field]) }}</button
                ><span v-else>{{ present(record[field]) }}</span>
              </dd>
            </div>
          </dl>
        </section>
        <section class="citation-preview">
          <h3>{{ i18n.t("record.citations") }}</h3>
          <div>
            <small>{{ i18n.t("record.inline_citation") }}</small>
            <p>{{ snapshot.inline_citation || "—" }}</p>
          </div>
          <div>
            <small>{{ i18n.t("record.full_citation") }}</small>
            <p>{{ snapshot.full_citation || "—" }}</p>
          </div>
        </section>
      </section>
      <RecordProvenance
        v-else-if="tab === 'provenance'"
        :id="panelId('provenance')"
        :record="record"
        :fields="provenanceFields"
        role="tabpanel"
        :aria-labelledby="tabId('provenance')"
        @search="(field, value) => emit('search', field, value)"
      />
      <section
        v-else-if="tab === 'indexing'"
        :id="panelId('indexing')"
        class="record-indexing-panel"
        role="tabpanel"
        :aria-labelledby="tabId('indexing')"
      >
        <div class="inspector-section-head">
          <p>{{ i18n.t("record.indexing_kicker") }}</p>
          <h2>{{ i18n.t("record.indexing") }}</h2>
          <button type="button" class="btn tiny record-layout-button" @click="layoutEditor?.open()">
            {{ i18n.t("record.configure_fields") }}
          </button>
        </div>
        <RecordIndexTerms
          v-for="key in indexingFields"
          :key="key"
          :title="fieldLabel(key)"
          :field="key"
          :values="values(key)"
          :editable="Boolean(snapshot.capabilities?.edit)"
          @search="(field, value) => emit('search', field, value, true)"
          @change="(field, next) => emit('change', { [field]: next })"
        />
      </section>
      <RecordPdfLinks
        v-else-if="tab === 'pdf'"
        :id="panelId('pdf')"
        role="tabpanel"
        :aria-labelledby="tabId('pdf')"
        :links="snapshot.pdf_links || []"
        :can-manage="Boolean(snapshot.capabilities?.edit && snapshot.capabilities?.pdf)"
        :can-open="Boolean(snapshot.capabilities?.pdf)"
        :pdf-loaded="Boolean(snapshot.pdf?.loaded)"
        :current-pdf="snapshot.pdf?.name || ''"
        @open="(index) => emit('openPdf', index)"
        @remove="(index) => emit('removePdf', index)"
        @remove-all="emit('removeAllPdf')"
        @explorer="emit('pdfExplorer')"
        @link-current="emit('linkCurrentPdf')"
      />
      <RecordAnnotations
        v-else-if="tab === 'annotations'"
        :id="panelId('annotations')"
        role="tabpanel"
        :aria-labelledby="tabId('annotations')"
        :annotations="snapshot.annotations || []"
        :can-add="Boolean(snapshot.capabilities?.annotate)"
        @add="emit('addAnnotation')"
        @remove="(id) => emit('removeAnnotation', id)"
      />
      <RecordHistoryTimeline
        v-else
        :id="panelId('history')"
        role="tabpanel"
        :aria-labelledby="tabId('history')"
        :items="snapshot.history || []"
        :total="snapshot.history_count || 0"
        :can-open="Boolean(snapshot.capabilities?.history)"
        @open="emit('openHistory')"
      />
    </div>
    <InspectorLayoutEditor ref="layoutEditor" :layout="layout" :record="record" @apply="applyLayout" @reset="resetLayout" />
  </aside>
</template>
<style scoped>
.record-inspector {
  position: sticky;
  top: 92px;
  max-height: calc(100dvh - 112px);
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}
.record-inspector-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  padding: 7px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-raised);
}
.record-inspector-tabs button {
  position: relative;
  min-width: 0;
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  padding: 5px 7px;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 780;
  line-height: 1.15;
  text-align: center;
  white-space: normal;
  cursor: pointer;
}
.record-inspector-tabs button:hover {
  background: var(--surface-raised);
  border-color: var(--line);
}
.record-inspector-tabs button.active {
  border-color: var(--line);
  background: var(--surface-raised);
  color: var(--text-2);
  box-shadow: var(--shadow-card);
}
.record-inspector-tabs button > span {
  min-width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.8125rem;
}
.record-layout-button {
  grid-column: 1 / -1;
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-2);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 750;
  cursor: pointer;
}
.inspector-field-group {
  display: grid;
  gap: 8px;
}
.inspector-field-group h3 {
  margin: 0;
  color: var(--text-2);
  font-size: 0.8125rem;
}
.record-inspector-body {
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: auto;
  padding: 15px 16px 18px;
  scrollbar-gutter: stable;
}
.record-overview-panel,
.record-indexing-panel {
  display: grid;
  gap: 17px;
}
.record-page-value {
  font-variant-numeric: tabular-nums;
}
.inspector-section-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: start;
}
.inspector-section-head p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.inspector-section-head h2 {
  margin: 2px 0 0;
  grid-column: 1;
  color: var(--text-2);
  font-size: 1.0625rem;
}
.inspector-section-head .record-layout-button {
  grid-column: 2;
  grid-row: 1 / span 2;
}
.record-meta-list {
  display: grid;
  margin: 0;
}
.record-meta-list > div {
  display: grid;
  grid-template-columns: minmax(100px, 0.68fr) minmax(0, 1fr);
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
}
.record-meta-list dt {
  color: var(--muted);
  font-size: 0.8125rem;
}
.record-meta-list dd {
  margin: 0;
  min-width: 0;
  color: var(--text-2);
  font-size: 0.78125rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.record-meta-list dd button {
  max-width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  color: var(--tone-ok-fg);
  font: inherit;
  text-align: left;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: #bdd3c6;
  text-underline-offset: 2px;
  overflow-wrap: anywhere;
}
.quoted-meta,
.citation-preview {
  display: grid;
  gap: 9px;
  padding-top: 2px;
}
.quoted-meta h3,
.citation-preview h3 {
  margin: 0;
  color: var(--text-2);
  font-size: 0.8125rem;
}
.citation-preview > div {
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-raised);
}
.citation-preview small {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
}
.citation-preview p {
  margin: 4px 0 0;
  color: var(--text-2);
  font:
    12.5px/1.5 Georgia,
    "Times New Roman",
    serif;
  overflow-wrap: anywhere;
}
.record-indexing-panel :deep(.record-index-terms + .record-index-terms) {
  padding-top: 15px;
  border-top: 1px solid var(--line);
}
button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 1180px) {
  .record-inspector {
    position: static;
    max-height: none;
  }
  .record-inspector-body {
    overflow: visible;
  }
}
@media (max-width: 520px) {
  .record-inspector-tabs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .record-meta-list > div {
    grid-template-columns: 1fr;
    gap: 3px;
  }
}
</style>

<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { toast } from "../composables/notifications";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { decompressUrlState } from "../domain/urlState";
import { useAuthStore } from "../stores/auth";
import { useRoute } from "vue-router";
import { sharedRecordWorkspace as recordWorkspace } from "../domain/sharedRecordWorkspace";
import { openSemanticRecord } from "../domain/semanticMapSources";
import { navigateTo } from "../domain/sharedNavigation";
import { useI18nStore } from "../stores/i18n";
import { useNewerData } from "../composables/useNewerData";
import NewerDataBanner from "../components/ui/NewerDataBanner.vue";
import { useShellStore } from "../stores/shell";
import RecordWorkspaceHeader from "../components/record/RecordWorkspaceHeader.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import RecordReadingPane from "../components/record/RecordReadingPane.vue";
import RecordInspector from "../components/record/RecordInspector.vue";
import RecordEditSheet from "../components/record/RecordEditSheet.vue";
import CorpusRecordSemanticMap from "../components/corpus-builder/CorpusRecordSemanticMap.vue";
import { corpusBuildsApi } from "../api/corpus";
import type { RecordWorkspaceSnapshot } from "../types/record";
import type { DerridaiNormativeModel, ResearchObjectGraph } from "../types/researchObjectGraph";
import { useSemanticMapStore } from "../stores/semanticMap";
import { annotationsService } from "../services/annotations";

const i18n = useI18nStore();
const shell = useShellStore();
const semanticMap = useSemanticMapStore();
const route = useRoute();
const auth = useAuthStore();
let readRequest = 0;
let semanticRequest = 0;
const snapshot = ref<RecordWorkspaceSnapshot>({ available: false, mode: "workspace" });
const loading = ref(true);
const error = ref("");
const objectGraph = ref<ResearchObjectGraph | null>(null);
const normativeModel = ref<DerridaiNormativeModel | null>(null);
const graphLoading = ref(false);
const graphError = ref("");
let graphRequest = 0;
const editOpen = ref(false);
const inspectorCollapsed = ref(false);
const inspectorWidth = ref(
  Math.max(
    310,
    Math.min(440, Number(localStorage.getItem("derridai.record.inspectorWidth") || 360) || 360),
  ),
);
const dragging = ref(false);
const annotationDialog = ref<HTMLDialogElement | null>(null);
const annotationQuote = ref("");
const annotationNote = ref("");
const annotationTags = ref("");
const annotationField = ref("text");
const annotationScope = ref<"text" | "record" | "work">("text");
const annotationParentId = ref<string | null>(null);
const annotationLinkedRecords = ref("");
const annotationError = ref("");
const recordSemanticBuildId = ref("");
const recordSemanticLoading = ref(false);
const showRecordMap = computed(
  () => semanticMap.enabled && semanticMap.placement === "record" && snapshot.value.available,
);

async function loadSemanticMap() {
  const request = ++semanticRequest;
  recordSemanticBuildId.value = "";
  const recordId = String(snapshot.value.record_id || "");
  if (!recordId) return;
  recordSemanticLoading.value = true;
  try {
    const result = await corpusBuildsApi
      .recordSemanticMapBuild(recordId)
      .catch(() => ({ build_id: null }));
    if (request === semanticRequest) recordSemanticBuildId.value = result.build_id || "";
  } finally {
    if (request === semanticRequest) recordSemanticLoading.value = false;
  }
}
function openSemanticMap() {
  semanticMap.enable(semanticMap.placement);
  void loadSemanticMap();
  if (semanticMap.placement === "page") navigateTo("semanticmap");
}

const record = computed(() => snapshot.value.record || {});
const work = computed(() =>
  String(record.value.work || record.value.document_title || i18n.t("record.untitled")),
);
const author = computed(() => String(record.value.document_author || ""));
const year = computed<string | number | null>(() => {
  const value = record.value.publication_year ?? record.value.year ?? null;
  return typeof value === "string" || typeof value === "number" ? value : null;
});
const positionLabel = computed(() =>
  snapshot.value.total && snapshot.value.current_index != null
    ? i18n.tf("record.position_of", {
        current: snapshot.value.current_index + 1,
        total: snapshot.value.total,
      })
    : "",
);
const badges = computed(() => {
  const out: Array<{ text: string; tone?: string }> = [];
  if (record.value.region_type) out.push({ text: String(record.value.region_type) });
  if (record.value.primary_text === false) out.push({ text: i18n.t("record.secondary_text") });
  else if (record.value.primary_text === true) out.push({ text: i18n.t("record.primary_text") });
  if (record.value.document_is_translation) out.push({ text: i18n.t("record.translation") });
  if (record.value.needs_review) out.push({ text: i18n.t("record.needs_review"), tone: "warn" });
  if (snapshot.value.mode === "database") out.push({ text: i18n.t("record.database_record") });
  else if (snapshot.value.file_name) out.push({ text: String(snapshot.value.file_name) });
  return out;
});

async function loadTraceability(current: RecordWorkspaceSnapshot) {
  const request = ++graphRequest;
  objectGraph.value = null;
  graphLoading.value = false;
  graphError.value = "";
  if (!current.available || !current.record) return;
  if (!String(current.record.record_id || "").trim()) {
    graphError.value = i18n.t(
      "traceability.missing_record_id",
      "This record does not yet have a durable record ID, so its traceability graph cannot be resolved.",
    );
    return;
  }
  graphLoading.value = true;
  try {
    const [graph, model] = await Promise.all([
      recordWorkspace.getRecordObjectGraph(current.record),
      recordWorkspace.getDerridaiNormativeModel(),
    ]);
    if (request !== graphRequest) return;
    objectGraph.value = graph as ResearchObjectGraph;
    normativeModel.value = model as DerridaiNormativeModel;
  } catch (exc) {
    if (request !== graphRequest) return;
    graphError.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (request === graphRequest) graphLoading.value = false;
  }
}
async function load() {
  const request = ++readRequest;
  loading.value = true;
  error.value = "";
  try {
    const next = (await recordWorkspace.getRecordWorkspaceSnapshot()) as RecordWorkspaceSnapshot;
    if (request !== readRequest) return;
    if (next.record_id !== snapshot.value.record_id) editOpen.value = false;
    snapshot.value = next;
    void loadTraceability(snapshot.value);
    loadSemanticMap();
  } catch (exc) {
    if (request !== readRequest) return;
    if (
      exc &&
      typeof exc === "object" &&
      "status" in exc &&
      [401, 403].includes(Number(exc.status))
    ) {
      clearSelection();
      loading.value = false;
    }
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (request === readRequest) loading.value = false;
  }
}
const newer = useNewerData();
async function loadNewer() {
  newer.acknowledge();
  await load();
}
async function refreshAfter(action: () => Promise<unknown> | unknown) {
  try {
    await action();
    await load();
  } catch (exc) {
    if (!snapshot.value.available) {
      loading.value = false;
      error.value = exc instanceof Error ? exc.message : String(exc);
    }
    toast(exc instanceof Error ? exc.message : String(exc), { tone: "danger" });
  }
}
async function previous() {
  clearSelection();
  await refreshAfter(() => recordWorkspace.recordWorkspaceNavigate(-1));
}
async function next() {
  clearSelection();
  await refreshAfter(() => recordWorkspace.recordWorkspaceNavigate(1));
}
function isTypingTarget(target: EventTarget | null) {
  const element = target as HTMLElement | null;
  return Boolean(element?.matches("input, textarea, select, [contenteditable='true']"));
}
function handleKeyboard(event: KeyboardEvent) {
  if (isTypingTarget(event.target)) return;
  if (event.altKey && event.key === "ArrowLeft" && snapshot.value.has_previous) {
    event.preventDefault();
    void previous();
  } else if (event.altKey && event.key === "ArrowRight" && snapshot.value.has_next) {
    event.preventDefault();
    void next();
  }
}
function setFind(value: string) {
  snapshot.value = { ...snapshot.value, find_query: value };
  recordWorkspace.setRecordWorkspaceFind(value);
}
async function toggleEvidence() {
  await refreshAfter(() => recordWorkspace.toggleCurrentRecordEvidence());
}
async function toggleReview() {
  await refreshAfter(() => recordWorkspace.toggleCurrentRecordReviewSelection());
}
async function saveChanges(changes: Record<string, unknown>) {
  await refreshAfter(() => recordWorkspace.saveCurrentRecordChanges(changes));
  editOpen.value = false;
}
async function quickChange(changes: Record<string, unknown>) {
  await refreshAfter(() => recordWorkspace.saveCurrentRecordChanges(changes));
}
function metadataSearch(field: string, value: string, contains = false) {
  recordWorkspace.searchCurrentRecordMetadata(field, value, { contains });
}
function openAnnotation(selection?: { field: string; quote: string }) {
  annotationField.value = selection?.field || "text";
  annotationScope.value = selection?.quote ? "text" : "record";
  annotationParentId.value = null;
  annotationLinkedRecords.value = "";
  annotationQuote.value = selection?.quote || "";
  annotationNote.value = "";
  annotationTags.value = "";
  annotationError.value = "";
  void nextTick(() => {
    if (annotationDialog.value && !annotationDialog.value.open) annotationDialog.value.showModal();
    annotationDialog.value?.querySelector<HTMLTextAreaElement>("#recordAnnotationNote")?.focus();
  });
}
function openReply(annotationId: string) {
  annotationField.value = "text";
  annotationScope.value = "record";
  annotationParentId.value = annotationId;
  annotationQuote.value = "";
  annotationNote.value = "";
  annotationTags.value = "";
  annotationLinkedRecords.value = "";
  annotationError.value = "";
  void nextTick(() => annotationDialog.value?.showModal());
}
function closeAnnotation() {
  annotationDialog.value?.close();
}
async function saveAnnotation() {
  annotationError.value = "";
  try {
    const tags = annotationTags.value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
    if (annotationParentId.value) {
      await annotationsService.replyToAnnotation(annotationParentId.value, {
        quote: annotationQuote.value,
        note: annotationNote.value,
        tags,
      });
    } else {
      await annotationsService.addToCurrentRecord({
        scope: annotationScope.value,
        linkedRecordIds: annotationLinkedRecords.value
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        field: annotationField.value,
        quote: annotationQuote.value,
        note: annotationNote.value,
        tags,
      });
    }
    closeAnnotation();
    await load();
  } catch (exc) {
    annotationError.value = exc instanceof Error ? exc.message : String(exc);
  }
}
async function removeAnnotation(id: string) {
  await refreshAfter(() => annotationsService.removeFromCurrentRecord(id));
}
async function action(name: string, payload: Record<string, unknown> = {}) {
  await refreshAfter(() => recordWorkspace.currentRecordPrimaryAction(name, payload));
}
function startResize(event: PointerEvent) {
  if (window.innerWidth < 1180) return;
  dragging.value = true;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  document.body.classList.add("record-resizing");
  window.addEventListener("pointermove", resize);
  window.addEventListener("pointerup", stopResize, { once: true });
}
function resize(event: PointerEvent) {
  if (!dragging.value) return;
  const workspace = document.querySelector(".record-workspace-grid")?.getBoundingClientRect();
  if (!workspace) return;
  const width = Math.max(310, Math.min(440, workspace.right - event.clientX));
  inspectorWidth.value = width;
}
function stopResize() {
  dragging.value = false;
  document.body.classList.remove("record-resizing");
  window.removeEventListener("pointermove", resize);
  localStorage.setItem("derridai.record.inspectorWidth", String(Math.round(inspectorWidth.value)));
}
function keyboardResize(event: KeyboardEvent) {
  if (window.innerWidth < 1180) return;
  let next = inspectorWidth.value;
  if (event.key === "ArrowLeft") next += 24;
  else if (event.key === "ArrowRight") next -= 24;
  else if (event.key === "Home") next = 310;
  else if (event.key === "End") next = 440;
  else return;
  event.preventDefault();
  inspectorWidth.value = Math.max(310, Math.min(440, next));
  localStorage.setItem("derridai.record.inspectorWidth", String(Math.round(inspectorWidth.value)));
}

const activeFileId = computed(() => shell.snapshot.files.find((file) => file.active)?.id || "");
// Ignore find-query URL changes: they do not change the authorized record identity.
const selectionKey = computed(() =>
  JSON.stringify([
    route.path,
    route.query.file,
    route.query.record,
    (decompressUrlState(String(route.query.ts || "")) as { rr?: string } | null)?.rr || "",
    activeFileId.value,
    shell.snapshot.activeStore,
    auth.user,
  ]),
);
function clearSelection() {
  loading.value = true;
  readRequest += 1;
  graphRequest += 1;
  semanticRequest += 1;
  snapshot.value = { available: false, mode: "workspace" };
  objectGraph.value = null;
  normativeModel.value = null;
  graphLoading.value = false;
  recordSemanticBuildId.value = "";
  recordSemanticLoading.value = false;
  editOpen.value = false;
  closeAnnotation();
}
watch(selectionKey, clearSelection, { flush: "sync" });
watch(selectionKey, () => {
  void load();
});
watch(
  () => i18n.locale,
  () => {
    void load();
  },
);
function onRecordUpdated() {
  void load();
}
onMounted(() => {
  window.addEventListener("derridai:record-updated", onRecordUpdated);
  window.addEventListener("keydown", handleKeyboard);
  void load();
});
onBeforeUnmount(() => {
  readRequest += 1;
  graphRequest += 1;
  semanticRequest += 1;
  window.removeEventListener("derridai:record-updated", onRecordUpdated);
  window.removeEventListener("keydown", handleKeyboard);
  window.removeEventListener("pointermove", resize);
  document.body.classList.remove("record-resizing");
});
</script>

<template>
  <main class="record-workspace-page" :aria-busy="loading && !snapshot.available">
    <NewerDataBanner :visible="newer.hasNewer.value" @load="loadNewer" />
    <div v-if="loading && !snapshot.available" class="record-workspace-loading" aria-busy="true">
      <h1>{{ i18n.t("loading.record_frame") }}</h1>
      <UiLoadingState :label="i18n.t('record.loading')" variant="skeleton" :skeleton-count="2" />
    </div>
    <section v-if="error" class="record-workspace-empty" role="alert">
      <p v-if="snapshot.available">{{ i18n.t("loading.stale") }}</p>
      <h1>{{ i18n.t("record.load_failed") }}</h1>
      <p>{{ error }}</p>
      <button type="button" @click="load()">{{ i18n.t("ui.retry") }}</button>
    </section>
    <section v-if="!loading && !error && !snapshot.available" class="record-workspace-empty">
      <h1>{{ i18n.t("record.no_record_selected") }}</h1>
      <p>
        {{ snapshot.reason || i18n.t("record.no_record_help") }}
      </p>
      <div>
        <button type="button" @click="recordWorkspace.navigateRecordWorkspace('global')">
          {{ i18n.t("nav.search") }}</button
        ><button type="button" @click="recordWorkspace.navigateRecordWorkspace('works')">
          {{ i18n.t("nav.works") }}
        </button>
      </div>
    </section>
    <template v-if="snapshot.available">
      <UiLoadingState v-if="loading" variant="inline" :label="i18n.t('loading.updating')" />
      <RecordWorkspaceHeader
        :work="work"
        :author="author"
        :year="year"
        :pages="snapshot.page_span || ''"
        :record-id="snapshot.record_id || ''"
        :position="positionLabel"
        :evidence-selected="snapshot.evidence_selected"
        :review-selected="snapshot.review_selected"
        :can-edit="snapshot.capabilities?.edit"
        :can-evidence="snapshot.capabilities?.evidence"
        :can-review="snapshot.capabilities?.review"
        :can-upsert="snapshot.capabilities?.upsert"
        :can-llm="snapshot.capabilities?.llm_review"
        :can-history="snapshot.capabilities?.history"
        :can-pdf="snapshot.capabilities?.pdf"
        :has-history="Boolean(snapshot.history_count)"
        :has-previous="snapshot.has_previous"
        :has-next="snapshot.has_next"
        @previous="previous"
        @next="next"
        @edit="editOpen = true"
        @evidence="toggleEvidence"
        @review="toggleReview"
        @copy-inline="recordWorkspace.copyCurrentRecordCitation('inline')"
        @copy-full="recordWorkspace.copyCurrentRecordCitation('full')"
        @copy-json="recordWorkspace.copyCurrentRecordJson()"
        @upsert="action('upsert')"
        @llm="action('llm')"
        @ocr="action('ocr')"
        @history="action('history')"
        @pdf="action('pdf_explorer')"
        @semantic-map="openSemanticMap"
      />

      <UiLoadingState
        v-if="showRecordMap && recordSemanticLoading"
        :label="i18n.t('pdf_corpus.semantic_map_calculating')"
      />
      <CorpusRecordSemanticMap
        v-else-if="showRecordMap && recordSemanticBuildId && snapshot.record_id"
        :build-id="recordSemanticBuildId"
        :record="{
          record_id: String(snapshot.record_id),
          text: typeof record.text === 'string' ? record.text : undefined,
          record_revision:
            typeof record.record_revision === 'number' ? record.record_revision : undefined,
        }"
        @open-record="openSemanticRecord($event)"
      />
      <p v-else-if="showRecordMap" class="info">
        {{ i18n.t("record.semantic_map_unavailable") }}
      </p>

      <div class="record-context-strip" :aria-label="i18n.t('record.status')">
        <span
          v-for="badge in badges"
          :key="badge.text"
          class="record-context-badge"
          :class="badge.tone"
          >{{ badge.text }}</span
        >
        <button
          v-if="snapshot.collection"
          type="button"
          class="record-context-link"
          @click="recordWorkspace.navigateRecordWorkspace('global')"
        >
          {{ i18n.t("record.collection") }}: {{ snapshot.collection }}
        </button>
        <span class="record-context-spacer"></span>
        <button
          type="button"
          class="record-inspector-toggle"
          :aria-expanded="!inspectorCollapsed"
          @click="inspectorCollapsed = !inspectorCollapsed"
        >
          {{
            inspectorCollapsed ? i18n.t("record.show_inspector") : i18n.t("record.hide_inspector")
          }}
        </button>
      </div>

      <section
        class="record-workspace-grid"
        :class="{ 'inspector-collapsed': inspectorCollapsed }"
        :style="{ '--record-inspector-width': `${inspectorWidth}px` }"
      >
        <RecordReadingPane
          :text="String(record.text || '')"
          :find-query="snapshot.find_query || ''"
          :word-count="snapshot.word_count || 0"
          :character-count="snapshot.character_count || 0"
          :annotations="snapshot.annotations || []"
          :can-annotate="snapshot.capabilities?.annotate"
          :summary-mode="snapshot.mode === 'database'"
          @find="setFind"
          @annotate="openAnnotation"
        />
        <div
          v-if="!inspectorCollapsed"
          class="record-inspector-resizer"
          role="separator"
          tabindex="0"
          aria-orientation="vertical"
          :aria-label="i18n.t('record.resize_inspector')"
          aria-valuemin="310"
          aria-valuemax="440"
          :aria-valuenow="Math.round(inspectorWidth)"
          @pointerdown="startResize"
          @keydown="keyboardResize"
        ></div>
        <RecordInspector
          v-if="!inspectorCollapsed"
          :snapshot="snapshot"
          :object-graph="objectGraph"
          :normative-model="normativeModel"
          :graph-loading="graphLoading"
          :graph-error="graphError"
          @search="metadataSearch"
          @change="quickChange"
          @add-annotation="openAnnotation()"
          @remove-annotation="removeAnnotation"
          @reply-annotation="openReply"
          @open-pdf="(index) => action('open_pdf', { index })"
          @remove-pdf="(index) => action('remove_pdf', { index })"
          @remove-all-pdf="action('remove_all_pdf')"
          @pdf-explorer="action('pdf_explorer')"
          @link-current-pdf="action('link_pdf')"
          @open-history="action('history')"
        />
      </section>

      <RecordEditSheet
        :open="editOpen"
        :record="record"
        @close="editOpen = false"
        @save="saveChanges"
      />

      <dialog
        ref="annotationDialog"
        class="record-annotation-dialog"
        aria-labelledby="recordAnnotationTitle"
        @cancel.prevent="closeAnnotation"
      >
        <form method="dialog" @submit.prevent="saveAnnotation">
          <header>
            <div>
              <p>{{ i18n.t("annotations.record_notes") }}</p>
              <h2 id="recordAnnotationTitle">
                {{
                  annotationParentId
                    ? i18n.t("annotations.reply")
                    : i18n.t("annotations.add_note_tags")
                }}
              </h2>
            </div>
            <button type="button" :aria-label="i18n.t('ui.close')" @click="closeAnnotation">
              ×
            </button>
          </header>
          <div class="record-annotation-form">
            <label v-if="!annotationParentId">
              <span>{{ i18n.t("annotations.scope") }}</span>
              <select v-model="annotationScope">
                <option value="text">{{ i18n.t("annotations.scope_text") }}</option>
                <option value="record">{{ i18n.t("annotations.scope_record") }}</option>
                <option value="work">{{ i18n.t("annotations.scope_work") }}</option>
              </select>
            </label>
            <blockquote v-if="annotationQuote">{{ annotationQuote }}</blockquote>
            <label v-if="!annotationParentId">
              <span>{{ i18n.t("annotations.linked_records") }}</span>
              <input
                v-model="annotationLinkedRecords"
                :placeholder="i18n.t('annotations.linked_records_placeholder')"
              />
            </label>
            <label
              ><span>{{ i18n.t("annotations.note") }}</span
              ><textarea
                id="recordAnnotationNote"
                v-model="annotationNote"
                rows="5"
                :placeholder="i18n.t('annotations.note_placeholder')"
              ></textarea>
            </label>
            <label
              ><span>{{ i18n.t("annotations.tags") }}</span
              ><input
                v-model="annotationTags"
                :placeholder="i18n.t('annotations.tags_placeholder')"
            /></label>
            <p v-if="annotationError" class="record-annotation-error" role="alert">
              {{ annotationError }}
            </p>
          </div>
          <footer>
            <button type="button" @click="closeAnnotation">
              {{ i18n.t("ui.cancel") }}</button
            ><button type="submit" class="primary">
              {{ i18n.t("annotations.save") }}
            </button>
          </footer>
        </form>
      </dialog>
    </template>
  </main>
</template>

<style scoped>
.record-workspace-page {
  display: grid;
  gap: var(--page-gap);
}
.record-workspace-loading,
.record-workspace-empty {
  min-height: 360px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  text-align: center;
}
.record-workspace-loading span {
  width: 34px;
  height: 34px;
  border: 3px solid var(--line);
  border-top-color: var(--ui-accent, #3c8d62);
  border-radius: 50%;
  animation: record-spin 0.8s linear infinite;
}
.record-workspace-empty h1 {
  margin: 0;
  font:
    600 26px/1.2 Georgia,
    "Times New Roman",
    serif;
}
.record-workspace-empty p {
  max-width: 600px;
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}
.record-workspace-empty > div {
  display: flex;
  gap: 8px;
}
.record-workspace-empty button {
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  padding: 0 12px;
  color: var(--text-2);
  font-weight: 800;
  cursor: pointer;
}
.record-context-strip {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  padding: 0 4px;
}
.record-context-badge,
.record-context-link {
  display: inline-flex;
  width: auto;
  max-width: 100%;
  min-height: 28px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  padding: 4px 9px;
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 750;
  white-space: normal;
  overflow-wrap: anywhere;
}
.record-context-badge.warn {
  border-color: var(--tone-warn-edge);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.record-context-link {
  cursor: pointer;
}
.record-context-spacer {
  flex: 1;
}
.record-inspector-toggle {
  min-height: 30px;
  border: 0;
  background: transparent;
  padding: 0 6px;
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
}
.record-workspace-grid {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 6px minmax(310px, var(--record-inspector-width, 360px));
  gap: 12px;
  align-items: start;
  min-width: 0;
}
.record-workspace-grid.inspector-collapsed {
  grid-template-columns: minmax(0, 1fr);
}
.record-inspector-resizer {
  align-self: stretch;
  width: 6px;
  min-height: 460px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  cursor: col-resize;
  position: relative;
}
.record-inspector-resizer:after {
  content: "";
  position: absolute;
  left: 3px;
  top: 36px;
  bottom: 36px;
  width: 2px;
  border-radius: 2px;
  background: var(--soft);
}
.record-inspector-resizer:hover:after,
.record-inspector-resizer:focus-visible:after {
  background: var(--ui-accent, #3c8d62);
}
.record-inspector-resizer:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 1px;
}
.record-annotation-dialog {
  width: min(560px, calc(100vw - 32px));
  max-width: none;
  border: 0;
  border-radius: var(--radius-overlay);
  padding: 0;
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.record-annotation-dialog::backdrop {
  background: rgba(15, 23, 42, 0.38);
  backdrop-filter: blur(2px);
}
.record-annotation-dialog header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: start;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
}
.record-annotation-dialog header p {
  margin: 0;
  color: var(--tone-ok-fg);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.record-annotation-dialog h2 {
  margin: 3px 0 0;
  font:
    600 21px/1.2 Georgia,
    "Times New Roman",
    serif;
}
.record-annotation-dialog header button {
  width: 36px;
  height: 36px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  font-size: 1.25rem;
  cursor: pointer;
}
.record-annotation-form {
  display: grid;
  gap: 14px;
  padding: 18px 20px;
}
.record-annotation-form blockquote {
  margin: 0;
  padding: 11px 12px;
  border-left: 3px solid var(--ui-accent, #3c8d62);
  border-radius: 0 8px 8px 0;
  background: var(--surface-inset);
  color: var(--text-2);
  font:
    13px/1.55 Georgia,
    "Times New Roman",
    serif;
}
.record-annotation-form label {
  display: grid;
  gap: 6px;
}
.record-annotation-form label span {
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.record-annotation-form textarea,
.record-annotation-form input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  padding: 9px 10px;
  font:
    13px/1.45 system-ui,
    sans-serif;
}
.record-annotation-form textarea {
  resize: vertical;
}
.record-annotation-error {
  margin: 0;
  padding: 9px 10px;
  border-radius: 8px;
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.record-annotation-dialog footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 13px 20px;
  border-top: 1px solid var(--line);
  background: var(--surface-raised);
}
.record-annotation-dialog footer button {
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  padding: 0 12px;
  color: var(--text-2);
  font-weight: 800;
  cursor: pointer;
}
.record-annotation-dialog footer .primary {
  border-color: var(--ui-accent, #3c8d62);
  background: var(--ui-accent, #3c8d62);
  color: var(--accent-on);
}
button:focus-visible,
textarea:focus-visible,
input:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@keyframes record-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 1180px) {
  .record-workspace-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .record-inspector-resizer {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .record-workspace-loading span {
    animation: none;
  }
}
</style>

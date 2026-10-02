<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  corpusCaptureApi,
  corpusSourcesApi,
  type CorpusCapture,
  type CorpusCaptureListItem,
  type SourceBulkDeleteResult,
  type SourceListResponse,
  type SourceRow,
} from "../api/corpus";
import { useI18nStore } from "../stores/i18n";
import { captureIsActive, enumLabel, enumTone } from "../domain/sourceLabels";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiStatusBadge from "../components/ui/UiStatusBadge.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import AppIcon from "../components/AppIcon.vue";
import SourceTable from "../components/sources/SourceTable.vue";
import SourceInspector from "../components/sources/SourceInspector.vue";
import CorpusCaptureDialog from "../components/capture/CorpusCaptureDialog.vue";

/**
 * Sources: every registered source with its provider, language and build state, the author
 * captures that gathered them, and bulk actions. Building stays in Corpus Builder; "Use in
 * Corpus Builder" hands the chosen ids over without starting anything.
 */
const i18n = useI18nStore();
const t = (key: string, fallback?: string) => i18n.t(key, fallback);
const route = useRoute();
const router = useRouter();

const captures = ref<CorpusCaptureListItem[]>([]);
const capturesError = ref("");
const selected = ref<string[]>([]);
const visibleRows = ref<SourceRow[]>([]);
const inspected = ref("");
const dialogOpen = ref(false);
const dialogCaptureId = ref("");
const busy = ref("");
const actionError = ref("");
const deleteResult = ref<SourceBulkDeleteResult | null>(null);
const confirmingDelete = ref(false);
/** Remounts the table (filters change); `reloadVersion` reloads it in place, keeping page and filters. */
const tableKey = ref(0);
const reloadVersion = ref(0);
/** A settled capture may have registered sources, including one that failed or stopped part-way. */
const SETTLED_CAPTURE = ["complete", "partial", "failed", "cancelled", "interrupted"];
const initialCapture = String(route.query.capture || "");

const captureLabels = computed(() =>
  Object.fromEntries(captures.value.map((capture) => [capture.capture_id, captureName(capture)])),
);
const selectedRows = computed(() =>
  visibleRows.value.filter((row) => selected.value.includes(row.source_document_id)),
);
/** Captures of the selected sources that have failed candidates to retry. */
const retryableCaptures = computed(() => {
  const ids = new Set(selectedRows.value.flatMap((row) => row.capture_ids));
  return captures.value.filter(
    (capture) =>
      ids.has(capture.capture_id) && Number(capture.summary?.acquisition?.failed || 0) > 0,
  );
});

function captureName(capture: CorpusCaptureListItem) {
  const years = [capture.author.birth_year, capture.author.death_year]
    .map((year) => (year === null || year === undefined ? "" : String(year)))
    .join("–");
  return years.replace("–", "")
    ? `${capture.author.canonical_name} (${years})`
    : capture.author.canonical_name;
}
function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
function fail(cause: unknown) {
  actionError.value = cause instanceof Error ? cause.message : String(cause);
}

async function loadCaptures() {
  try {
    captures.value = (await corpusCaptureApi.listCaptures()).items;
    capturesError.value = "";
  } catch (cause) {
    capturesError.value = cause instanceof Error ? cause.message : String(cause);
  }
}
function onLoaded(response: SourceListResponse) {
  visibleRows.value = response.items;
}
function openCapture(captureId = "") {
  dialogCaptureId.value = captureId;
  dialogOpen.value = true;
}
function onCaptureChanged(capture: CorpusCapture) {
  const index = captures.value.findIndex((item) => item.capture_id === capture.capture_id);
  const row: CorpusCaptureListItem = {
    capture_id: capture.capture_id,
    author: capture.author,
    status: capture.status,
    phase: capture.phase,
    created_at: capture.created_at,
    discovery_completed_at: capture.discovery_completed_at,
    last_refreshed_at: capture.last_refreshed_at,
    summary: capture.summary,
  };
  if (index >= 0) captures.value.splice(index, 1, row);
  else captures.value.unshift(row);
  // New sources appear only when an acquisition settles.
  if (!capture.active_job && SETTLED_CAPTURE.includes(capture.status)) reloadVersion.value += 1;
}
async function refreshCapture(captureId: string) {
  busy.value = `refresh:${captureId}`;
  actionError.value = "";
  try {
    onCaptureChanged(await corpusCaptureApi.refresh(captureId));
    openCapture(captureId);
  } catch (cause) {
    fail(cause);
  } finally {
    busy.value = "";
  }
}
async function retryCaptures(ids: string[]) {
  busy.value = "retry";
  actionError.value = "";
  try {
    for (const id of ids) onCaptureChanged(await corpusCaptureApi.retry(id));
  } catch (cause) {
    fail(cause);
  } finally {
    busy.value = "";
  }
}
function useInBuilder(ids: string[]) {
  dialogOpen.value = false;
  window.dispatchEvent(
    new CustomEvent("derridai:navigate-native", {
      detail: {
        path: `/corpus-builder?sources=${encodeURIComponent(ids.join(","))}`,
        runtimeView: "pdf",
      },
    }),
  );
}
/** Closing stops the dialog's polling, so reload in case sources arrived meanwhile. */
function closeCapture() {
  dialogOpen.value = false;
  reloadVersion.value += 1;
}
function viewCaptureSources(captureId: string) {
  dialogOpen.value = false;
  void router.replace({ query: { ...route.query, capture: captureId } });
  tableKey.value += 1;
}
async function removeSelected() {
  confirmingDelete.value = false;
  busy.value = "delete";
  actionError.value = "";
  try {
    const result = await corpusSourcesApi.bulkDeleteSources(selected.value);
    deleteResult.value = result;
    const removed = new Set(
      result.items.filter((item) => item.deleted).map((item) => item.source_document_id),
    );
    selected.value = selected.value.filter((id) => !removed.has(id));
    if (removed.size) reloadVersion.value += 1;
  } catch (cause) {
    fail(cause);
  } finally {
    busy.value = "";
  }
}
function titleOf(id: string) {
  return visibleRows.value.find((row) => row.source_document_id === id)?.title || id;
}
function refusalText(item: SourceBulkDeleteResult["items"][number]) {
  return item.reason === "in_use"
    ? i18n.tf("sources.bulk.refused_in_use", {
        title: titleOf(item.source_document_id),
        reason: item.message || "",
      })
    : i18n.tf("sources.bulk.refused_missing", { title: titleOf(item.source_document_id) });
}
onMounted(() => void loadCaptures());
</script>

<template>
  <main class="vue-native-page sources-page" aria-labelledby="sources-title">
    <UiPageHeader
      :kicker="i18n.t('section.corpus_management')"
      :title="i18n.t('sources.title')"
      title-id="sources-title"
      :description="i18n.t('sources.help')"
    >
      <template #actions>
        <UiButton
          variant="primary"
          icon="users"
          :label="i18n.t('capture.path_title')"
          data-action="capture"
          @click="openCapture()"
        />
      </template>
    </UiPageHeader>

    <p v-if="actionError" class="sources-error" role="alert">
      <AppIcon name="warning" /><span>{{ actionError }}</span>
    </p>

    <section class="captures" aria-labelledby="captures-title">
      <h2 id="captures-title">{{ i18n.t("sources.captures.title") }}</h2>
      <p v-if="capturesError" class="sources-error" role="alert">{{ capturesError }}</p>
      <p v-else-if="!captures.length" class="sources-muted">
        {{ i18n.t("sources.captures.none") }}
      </p>
      <ul v-else class="capture-list">
        <li
          v-for="capture in captures"
          :key="capture.capture_id"
          :data-capture="capture.capture_id"
        >
          <div class="capture-main">
            <strong>{{ captureName(capture) }}</strong>
            <UiStatusBadge
              :label="enumLabel(t, 'capture_status', capture.status)"
              :tone="enumTone('capture_status', capture.status)"
            />
          </div>
          <small class="sources-muted">
            {{
              i18n.tf("sources.captures.counts", {
                sources: capture.summary?.candidates ?? 0,
                registered: capture.summary?.acquisition?.registered ?? 0,
                failed: capture.summary?.acquisition?.failed ?? 0,
              })
            }}
            ·
            {{
              i18n.tf("sources.captures.last_discovered", {
                date: formatDate(capture.last_refreshed_at || capture.discovery_completed_at),
              })
            }}
          </small>
          <div class="capture-actions">
            <button type="button" class="btn small" @click="openCapture(capture.capture_id)">
              {{ i18n.t("sources.captures.open") }}
            </button>
            <button
              type="button"
              class="btn small"
              data-action="refresh-capture"
              :disabled="
                captureIsActive(capture.status) || !capture.discovery_completed_at || busy !== ''
              "
              @click="refreshCapture(capture.capture_id)"
            >
              <AppIcon name="refresh" />{{ i18n.t("capture.dialog.refresh") }}
            </button>
            <button
              v-if="(capture.summary?.acquisition?.failed ?? 0) > 0"
              type="button"
              class="btn small"
              :disabled="captureIsActive(capture.status) || busy !== ''"
              @click="retryCaptures([capture.capture_id])"
            >
              {{
                i18n.tf("capture.done.retry_failed", { count: capture.summary.acquisition.failed })
              }}
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section class="sources-workspace" aria-labelledby="sources-table-title">
      <h2 id="sources-table-title">{{ i18n.t("sources.table.title") }}</h2>
      <div
        v-if="selected.length"
        class="bulk-bar"
        role="toolbar"
        :aria-label="i18n.t('sources.bulk.label')"
      >
        <span role="status">{{
          i18n.tf("sources.bulk.selected", { count: selected.length })
        }}</span>
        <button
          type="button"
          class="btn small primary"
          data-bulk="builder"
          @click="useInBuilder(selected)"
        >
          {{ i18n.t("capture.done.use_in_builder") }}
        </button>
        <UiTooltip
          v-if="!retryableCaptures.length"
          :text="i18n.t('sources.bulk.retry_none')"
          trigger-mode="content"
          placement="bottom"
        >
          <button type="button" class="btn small" data-bulk="retry" disabled>
            {{ i18n.t("sources.bulk.retry") }}
          </button>
        </UiTooltip>
        <button
          v-else
          type="button"
          class="btn small"
          data-bulk="retry"
          :disabled="busy !== ''"
          @click="retryCaptures(retryableCaptures.map((capture) => capture.capture_id))"
        >
          {{ i18n.t("sources.bulk.retry") }}
        </button>
        <button
          v-if="!confirmingDelete"
          type="button"
          class="btn small danger"
          data-bulk="remove"
          :disabled="busy !== ''"
          @click="confirmingDelete = true"
        >
          {{ i18n.t("sources.bulk.remove") }}
        </button>
        <span v-else class="bulk-confirm" role="group">
          {{ i18n.tf("sources.bulk.remove_confirm", { count: selected.length }) }}
          <button
            type="button"
            class="btn small danger"
            data-bulk="remove-confirm"
            @click="removeSelected"
          >
            {{ i18n.t("sources.bulk.remove") }}
          </button>
          <button type="button" class="btn small" @click="confirmingDelete = false">
            {{ i18n.t("common.cancel") }}
          </button>
        </span>
        <button type="button" class="btn small quiet" @click="selected = []">
          {{ i18n.t("sources.bulk.clear") }}
        </button>
      </div>
      <div v-if="deleteResult" class="delete-result" role="status">
        <p>
          {{
            i18n.tf("sources.bulk.removed", {
              count: deleteResult.items.filter((item) => item.deleted).length,
            })
          }}
        </p>
        <ul v-if="deleteResult.items.some((item) => !item.deleted)">
          <li
            v-for="item in deleteResult.items.filter((entry) => !entry.deleted)"
            :key="item.source_document_id"
            :data-refused="item.reason"
          >
            {{ refusalText(item) }}
          </li>
        </ul>
        <button type="button" class="btn small quiet" @click="deleteResult = null">
          {{ i18n.t("common.close") }}
        </button>
      </div>

      <div class="sources-layout" :class="{ 'has-inspector': inspected }">
        <SourceTable
          :key="tableKey"
          :refresh-key="reloadVersion"
          v-model:selected="selected"
          :capture-labels="captureLabels"
          :initial-filters="initialCapture ? { capture_id: initialCapture } : {}"
          :page-size="50"
          @inspect="inspected = $event"
          @loaded="onLoaded"
        />
        <SourceInspector
          v-if="inspected"
          :source-id="inspected"
          :capture-labels="captureLabels"
          @close="inspected = ''"
        />
      </div>
    </section>

    <CorpusCaptureDialog
      v-if="dialogOpen"
      :open="dialogOpen"
      :capture-id="dialogCaptureId"
      @close="closeCapture"
      @changed="onCaptureChanged"
      @use-in-builder="useInBuilder"
      @view-sources="viewCaptureSources"
    />
  </main>
</template>

<style scoped>
.sources-page {
  display: grid;
  gap: var(--page-gap, 12px);
  align-content: start;
}
h2 {
  margin: 0 0 8px;
  font-size: var(--fs-lg);
}
.captures,
.sources-workspace {
  display: grid;
  gap: 8px;
  min-width: 0;
}
.capture-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.capture-list li {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.capture-main,
.capture-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.sources-muted {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.sources-error {
  display: flex;
  gap: 6px;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--tone-danger-border);
  border-radius: var(--radius-control);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.bulk-bar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
}
.bulk-bar > span[role="status"] {
  font-weight: var(--fw-semibold);
}
.bulk-confirm {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.delete-result {
  padding: 8px 10px;
  border: 1px solid var(--tone-warn-border);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.delete-result p,
.delete-result ul {
  margin: 0 0 6px;
}
.sources-layout {
  display: grid;
  gap: 12px;
  min-width: 0;
}
.sources-layout.has-inspector {
  grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
  align-items: start;
}
@media (max-width: 1100px) {
  .sources-layout.has-inspector {
    grid-template-columns: 1fr;
  }
}
</style>

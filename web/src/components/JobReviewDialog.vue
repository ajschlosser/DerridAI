<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useJobReviewDialog, type JobReviewApplyMode } from "../composables/jobReviewDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useJobReviewDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const selected = ref<Set<number>>(new Set());
const busy = ref(false);

const view = computed(() => current.value?.view ?? null);

function defaultSelection() {
  const rows = view.value?.rows ?? [];
  selected.value = new Set(rows.flatMap((row, index) => (row.isText ? [] : [index])));
}

// A republished view keeps the reviewer's selection where it still applies, as the legacy dialog did.
watch(view, (next, previous) => {
  if (!next) return;
  if (!previous) return defaultSelection();
  const kept = [...selected.value].filter((index) => index < next.rows.length);
  if (kept.length) selected.value = new Set(kept);
  else defaultSelection();
});

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  () => current.value !== null,
  async (isOpen) => {
    await nextTick();
    const dialog = dialogRef.value;
    if (!dialog) return;
    if (!isOpen) {
      if (dialog.open) dialog.close();
    } else if (!dialog.open) {
      defaultSelection();
      dialog.showModal();
    }
  },
  { immediate: true },
);

function toggle(index: number, on: boolean) {
  const next = new Set(selected.value);
  if (on) next.add(index);
  else next.delete(index);
  selected.value = next;
}

async function run(action: () => Promise<boolean>) {
  if (busy.value) return;
  busy.value = true;
  try {
    if (await action()) defaultSelection();
  } finally {
    busy.value = false;
  }
}

const picked = () => [...selected.value].sort((a, b) => a - b);
const apply = (mode: JobReviewApplyMode) => run(() => current.value!.actions.apply(mode, picked()));
const rejectSelected = () => run(() => current.value!.actions.rejectSelected(picked()));
</script>

<template>
  <dialog
    ref="dialogRef"
    class="job-results-dialog"
    aria-labelledby="jobReviewTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="view && current">
      <div class="dh">
        <div>
          <h2 id="jobReviewTitle" class="dialog-title">{{ view.title }}</h2>
          <div class="dialog-subtitle">{{ view.subtitle }}</div>
        </div>
        <div class="tools">
          <span v-if="view.active" class="job-status running">{{
            i18n.t("jobs.review.live")
          }}</span>
          <button
            class="btn icon-only"
            type="button"
            :aria-label="i18n.t('ui.close')"
            @click="close()"
          >
            ×
          </button>
        </div>
      </div>
      <div class="db job-change-review">
        <div class="job-resolution-summary">
          <span
            ><b>{{ view.resolution.acceptedResults }}</b>
            {{ i18n.t("jobs.review.accepted_results") }}</span
          >
          <span
            ><b>{{ view.resolution.acceptedFields }}</b>
            {{ i18n.t("jobs.review.accepted_fields") }}</span
          >
          <span
            ><b>{{ view.resolution.rejectedResults }}</b>
            {{ i18n.t("jobs.review.rejected_results") }}</span
          >
          <span
            ><b>{{ view.resolution.rejectedFields }}</b>
            {{ i18n.t("jobs.review.rejected_fields") }}</span
          >
          <span
            ><b>{{ view.resolution.state }}</b> {{ i18n.t("jobs.review.decision_state") }}</span
          >
        </div>
        <div v-if="view.rows.length" class="job-change-toolbar">
          <button
            class="btn small"
            type="button"
            @click="selected = new Set(view.rows.map((_, index) => index))"
          >
            {{ i18n.t("jobs.review.select_all") }}
          </button>
          <button class="btn small" type="button" @click="selected = new Set()">
            {{ i18n.t("jobs.review.select_none") }}
          </button>
          <button class="btn small danger" type="button" :disabled="busy" @click="rejectSelected()">
            {{ i18n.t("jobs.review.reject_selected") }}
          </button>
          <span class="note"
            ><b>{{ selected.size }}</b> {{ i18n.t("jobs.review.selected_help") }}</span
          >
        </div>
        <div v-if="view.failures.length" class="info warn" role="status">
          <template v-for="(failure, index) in view.failures" :key="index"
            ><br v-if="index" />{{ failure }}</template
          >
        </div>
        <div v-if="view.rows.length" class="job-change-table-wrap">
          <table class="job-change-table">
            <thead>
              <tr>
                <th>
                  <span class="sr-only">{{ i18n.t("jobs.review.select_all") }}</span>
                </th>
                <th>{{ i18n.t("jobs.review.record_col") }}</th>
                <th>{{ i18n.t("works.field") }}</th>
                <th>{{ i18n.t("jobs.review.current") }}</th>
                <th>{{ i18n.t("jobs.review.proposed") }}</th>
                <th>{{ i18n.t("jobs.review.rationale") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, index) in view.rows"
                :key="index"
                :class="{ 'stale-change': row.stale }"
              >
                <td>
                  <input
                    type="checkbox"
                    :checked="selected.has(index)"
                    :aria-label="`${row.recordId} · ${row.field}`"
                    @change="toggle(index, ($event.target as HTMLInputElement).checked)"
                  />
                </td>
                <td>
                  <div class="job-record-cell">
                    <b>{{ row.recordId }}</b>
                    <button
                      v-if="row.copyKey"
                      class="btn tiny"
                      type="button"
                      :data-copy-row-key="row.copyKey"
                    >
                      {{ i18n.t("ui.copy") }}
                    </button>
                    <button
                      class="btn tiny"
                      type="button"
                      @click="current.actions.previewRow(index)"
                    >
                      {{ i18n.t("jobs.review.preview") }}
                    </button>
                    <span v-if="row.stale" class="stale-badge">{{
                      i18n.t("jobs.review.stale")
                    }}</span>
                  </div>
                </td>
                <td>
                  <b>{{ row.field }}</b>
                </td>
                <!-- eslint-disable vue/no-v-html -- escaped by the shared diff renderer -->
                <td><pre class="change-diff current-diff" v-html="row.currentHtml"></pre></td>
                <td><pre class="change-diff proposed-diff" v-html="row.proposedHtml"></pre></td>
                <!-- eslint-enable vue/no-v-html -->
                <td>{{ row.rationale || i18n.t("jobs.review.no_rationale") }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <section v-else class="review-no-changes-empty">
          <div class="review-no-changes-icon" aria-hidden="true">✓</div>
          <div>
            <h3>
              {{
                view.active
                  ? i18n.t("jobs.review.no_pending_yet")
                  : i18n.t("jobs.review.no_changes")
              }}
            </h3>
            <p>
              {{
                view.active
                  ? i18n.tf("jobs.review.still_running", {
                      completed: view.completed.toLocaleString(),
                      remaining: view.remaining.toLocaleString(),
                    })
                  : i18n.tf("jobs.review.none_proposed", {
                      count: view.noChangeCount.toLocaleString(),
                    })
              }}
            </p>
          </div>
        </section>
        <details v-if="view.noChangeCount" class="unchanged-review-list" :open="!view.rows.length">
          <summary>
            <span
              ><b>{{
                i18n.tf("jobs.review.no_change_count", {
                  count: view.noChangeCount.toLocaleString(),
                })
              }}</b
              ><small>{{ i18n.t("jobs.review.expand_inspect") }}</small></span
            >
          </summary>
          <div class="unchanged-review-grid">
            <div v-for="(item, index) in view.unchanged" :key="index" class="unchanged-review-row">
              <div>
                <b>{{ item.recordId }}</b
                ><span
                  >{{ item.work
                  }}<template v-if="item.stale">
                    · {{ i18n.t("jobs.review.stale_review") }}</template
                  ></span
                >
              </div>
              <button
                class="btn tiny"
                type="button"
                @click="current.actions.previewUnchanged(index)"
              >
                {{ i18n.t("jobs.review.preview") }}
              </button>
            </div>
          </div>
        </details>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.close") }}</button>
        <button
          v-if="view.discard !== 'none'"
          class="btn danger subtle-danger"
          type="button"
          @click="current.actions.discard()"
        >
          {{
            view.discard === "stop"
              ? i18n.t("jobs.review.stop_discard")
              : i18n.t("jobs.review.discard_remove")
          }}
        </button>
        <button v-if="view.active" class="btn" type="button" @click="current.actions.refresh()">
          {{ i18n.t("jobs.review.refresh") }}
        </button>
        <template v-if="view.hasSuccessful">
          <button class="btn" type="button" :disabled="busy" @click="apply('review')">
            {{ i18n.t("jobs.review.mark_reviewed") }}
          </button>
          <template v-if="view.rows.length">
            <button
              class="btn primary"
              type="button"
              :disabled="busy || !selected.size"
              @click="apply('selected')"
            >
              {{ i18n.t("jobs.review.apply_selected") }}
            </button>
            <button class="btn soft" type="button" :disabled="busy" @click="apply('all')">
              {{ i18n.t("jobs.review.accept_all") }}
            </button>
          </template>
        </template>
      </div>
    </template>
  </dialog>
</template>

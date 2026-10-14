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
import { nextTick, ref, watch } from "vue";
import { useRecordPreviewDialog } from "../composables/recordPreviewDialog";
import { useI18nStore } from "../stores/i18n";

const { current, close } = useRecordPreviewDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    await nextTick();
    const dialog = dialogRef.value;
    if (!dialog) return;
    if (!request) {
      if (dialog.open) dialog.close();
    } else if (!dialog.open) {
      dialog.showModal();
    }
  },
  { immediate: true },
);

function openFull() {
  const request = current.value;
  close();
  request?.openFull();
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="record-preview-dialog"
    aria-labelledby="recordPreviewTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="dh">
        <div>
          <h2 id="recordPreviewTitle" class="dialog-title">{{ i18n.t("jobs.preview.title") }}</h2>
          <div class="dialog-subtitle">{{ current.recordId }} · {{ current.subtitle }}</div>
        </div>
        <button
          class="btn icon-only"
          type="button"
          :aria-label="i18n.t('ui.close')"
          @click="close()"
        >
          ×
        </button>
      </div>
      <div class="db record-preview-body">
        <div v-if="current.stale" class="info warn" role="status">
          {{ i18n.t("jobs.preview.stale") }}
        </div>
        <section class="record-preview-summary">
          <div>
            <span>{{ i18n.t("jobs.preview.record_id") }}</span
            ><b>{{ current.recordId }}</b>
          </div>
          <div>
            <span>{{ i18n.t("jobs.preview.work") }}</span
            ><b>{{ current.summary.work }}</b>
          </div>
          <div>
            <span>{{ i18n.t("jobs.preview.pages") }}</span
            ><b>{{ current.summary.pages }}</b>
          </div>
          <div>
            <span>{{ i18n.t("jobs.preview.citation") }}</span
            ><b>{{ current.summary.citation }}</b>
          </div>
          <div>
            <span>{{ i18n.t("jobs.preview.llm_proposals") }}</span
            ><b>{{ current.summary.proposalCount }}</b>
          </div>
          <div>
            <span>{{ i18n.t("jobs.preview.needs_review") }}</span
            ><b>{{ current.summary.needsReview ? i18n.t("common.yes") : i18n.t("common.no") }}</b>
          </div>
        </section>

        <section class="record-preview-section">
          <div class="record-preview-heading">
            <b>{{ i18n.t("jobs.preview.metadata") }}</b>
            <span>{{
              i18n.tf("jobs.preview.populated_fields", { count: current.fields.length })
            }}</span>
          </div>
          <div class="record-preview-metadata">
            <div
              v-for="field in current.fields"
              :key="field.key"
              class="record-preview-field"
              :class="{ 'proposed-field': field.proposed }"
            >
              <span
                >{{ field.label
                }}<i v-if="field.proposed">{{ i18n.t("jobs.preview.proposed_change") }}</i></span
              >
              <pre>{{ field.value }}</pre>
            </div>
          </div>
        </section>

        <section class="record-preview-section">
          <div class="record-preview-heading">
            <b>{{ i18n.t("jobs.preview.text") }}</b>
            <span>{{
              i18n.tf("jobs.preview.characters", { count: current.text.length.toLocaleString() })
            }}</span>
          </div>
          <pre class="record-preview-text">{{ current.text }}</pre>
        </section>

        <section v-if="current.proposals.length" class="record-preview-section">
          <div class="record-preview-heading">
            <b>{{ i18n.t("jobs.preview.proposed_for_record") }}</b>
            <span>{{ current.proposals.length }}</span>
          </div>
          <div class="record-preview-proposals">
            <div v-for="proposal in current.proposals" :key="proposal.label">
              <b>{{ proposal.label }}</b>
              <div class="record-preview-proposal-grid">
                <pre>{{ proposal.current }}</pre>
                <span>→</span>
                <pre>{{ proposal.proposed }}</pre>
              </div>
              <small v-if="proposal.rationale">{{ proposal.rationale }}</small>
            </div>
          </div>
        </section>

        <section class="record-preview-section">
          <div class="record-preview-heading">
            <b>{{ i18n.t("jobs.preview.audit") }}</b>
            <span>{{ i18n.tf("jobs.preview.shown", { count: current.history.length }) }}</span>
          </div>
          <div class="record-preview-history">
            <div v-for="(entry, n) in current.history" :key="n">
              <time>{{ entry.when }}</time>
              <b>{{ entry.field }}</b>
              <span>{{ entry.source }}</span>
            </div>
            <div v-if="!current.history.length" class="note">
              {{ i18n.t("jobs.preview.no_audit") }}
            </div>
          </div>
        </section>
      </div>
      <div class="da">
        <button class="btn" type="button" @click="close()">
          {{ i18n.t("jobs.preview.close") }}
        </button>
        <button class="btn" type="button" :data-copy-row-key="current.copyKey">
          {{ i18n.t("pdf.copy_entire") }}
        </button>
        <button class="btn primary" type="button" @click="openFull()">
          {{ i18n.t("jobs.preview.open_full") }}
        </button>
      </div>
    </template>
  </dialog>
</template>

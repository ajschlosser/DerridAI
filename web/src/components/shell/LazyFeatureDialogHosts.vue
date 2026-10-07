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
import { defineAsyncComponent, ref, watch, type Ref } from "vue";
import { useBulkFieldEditorDialog } from "../../composables/bulkFieldEditorDialog";
import { useJobDetailsDialog } from "../../composables/jobDetailsDialog";
import { useJobReviewDialog } from "../../composables/jobReviewDialog";
import { useLlmTaskLauncherDialog } from "../../composables/llmTaskLauncherDialog";
import { useLlmToolResultDialog } from "../../composables/llmToolResultDialog";
import { useMergeFilesDialog } from "../../composables/mergeFilesDialog";
import { useMixedWorkValuesDialog } from "../../composables/mixedWorkValuesDialog";
import { useOcrCleanupDialog } from "../../composables/ocrCleanupDialog";
import { usePdfDraftRecordDialog } from "../../composables/pdfDraftRecordDialog";
import { useRecordFieldEditorDialog } from "../../composables/recordFieldEditorDialog";
import { useRecordHistoryDialog } from "../../composables/recordHistoryDialog";
import { useRecordPreviewDialog } from "../../composables/recordPreviewDialog";
import { useRemoveWorkDialog } from "../../composables/removeWorkDialog";
import { useSeparateWorksDialog } from "../../composables/separateWorksDialog";
import { useUpsertQueueDialog } from "../../composables/upsertQueueDialog";
import { useWorkMetadataEditorDialog } from "../../composables/workMetadataEditor";
import { useWorkMetadataLlmDialog } from "../../composables/workMetadataLlmDialog";
import { useWorkMetadataProposalDialog } from "../../composables/workMetadataProposalDialog";
import { useTouchupWorkspaceRequest } from "../../features/touchup/touchupWorkspaceRequest";

/**
 * Feature dialogs are globally addressable commands, but their implementations
 * are not application chrome. Keep only their tiny request refs resident and
 * load each dialog implementation on first use. Once activated, a host remains
 * mounted so the dialog can observe its request closing and restore focus before
 * the native <dialog> leaves the DOM.
 */
function activatedBy(current: Readonly<Ref<unknown>>): Ref<boolean> {
  const activated = ref(Boolean(current.value));
  watch(
    current,
    (request) => {
      if (request) activated.value = true;
    },
    { immediate: true },
  );
  return activated;
}

const BulkFieldEditorDialog = defineAsyncComponent(() => import("../BulkFieldEditorDialog.vue"));
const JobDetailsDialog = defineAsyncComponent(() => import("../JobDetailsDialog.vue"));
const JobReviewDialog = defineAsyncComponent(() => import("../JobReviewDialog.vue"));
const LlmReviewWorkspace = defineAsyncComponent(() => import("../LlmReviewWorkspace.vue"));
const LlmTaskLauncherDialog = defineAsyncComponent(() => import("../LlmTaskLauncherDialog.vue"));
const LlmToolResultDialog = defineAsyncComponent(() => import("../LlmToolResultDialog.vue"));
const MergeFilesDialog = defineAsyncComponent(() => import("../MergeFilesDialog.vue"));
const MixedWorkValuesDialog = defineAsyncComponent(() => import("../MixedWorkValuesDialog.vue"));
const OcrCleanupDialog = defineAsyncComponent(() => import("../OcrCleanupDialog.vue"));
const PdfDraftRecordDialog = defineAsyncComponent(() => import("../PdfDraftRecordDialog.vue"));
const RecordFieldEditorDialog = defineAsyncComponent(() => import("../RecordFieldEditorDialog.vue"));
const RecordHistoryDialog = defineAsyncComponent(() => import("../RecordHistoryDialog.vue"));
const RecordPreviewDialog = defineAsyncComponent(() => import("../RecordPreviewDialog.vue"));
const RemoveWorkDialog = defineAsyncComponent(() => import("../RemoveWorkDialog.vue"));
const SeparateWorksDialog = defineAsyncComponent(() => import("../SeparateWorksDialog.vue"));
const UpsertQueueDialog = defineAsyncComponent(() => import("../UpsertQueueDialog.vue"));
const WorkMetadataEditorDialog = defineAsyncComponent(() => import("../WorkMetadataEditorDialog.vue"));
const WorkMetadataLlmDialog = defineAsyncComponent(() => import("../WorkMetadataLlmDialog.vue"));
const WorkMetadataProposalDialog = defineAsyncComponent(
  () => import("../WorkMetadataProposalDialog.vue"),
);

const bulkFieldEditorActive = activatedBy(useBulkFieldEditorDialog().current);
const jobDetailsActive = activatedBy(useJobDetailsDialog().current);
const jobReviewActive = activatedBy(useJobReviewDialog().current);
const llmReviewWorkspaceActive = activatedBy(useTouchupWorkspaceRequest().current);
const llmTaskLauncherActive = activatedBy(useLlmTaskLauncherDialog().current);
const llmToolResultActive = activatedBy(useLlmToolResultDialog().current);
const mergeFilesActive = activatedBy(useMergeFilesDialog().current);
const mixedWorkValuesActive = activatedBy(useMixedWorkValuesDialog().current);
const ocrCleanupActive = activatedBy(useOcrCleanupDialog().current);
const pdfDraftRecordActive = activatedBy(usePdfDraftRecordDialog().current);
const recordFieldEditorActive = activatedBy(useRecordFieldEditorDialog().current);
const recordHistoryActive = activatedBy(useRecordHistoryDialog().current);
const recordPreviewActive = activatedBy(useRecordPreviewDialog().current);
const removeWorkActive = activatedBy(useRemoveWorkDialog().current);
const separateWorksActive = activatedBy(useSeparateWorksDialog().current);
const upsertQueueActive = activatedBy(useUpsertQueueDialog().current);
const workMetadataEditorActive = activatedBy(useWorkMetadataEditorDialog().current);
const workMetadataLlmActive = activatedBy(useWorkMetadataLlmDialog().current);
const workMetadataProposalActive = activatedBy(useWorkMetadataProposalDialog().current);
</script>

<template>
  <BulkFieldEditorDialog v-if="bulkFieldEditorActive" />
  <JobDetailsDialog v-if="jobDetailsActive" />
  <JobReviewDialog v-if="jobReviewActive" />
  <LlmReviewWorkspace v-if="llmReviewWorkspaceActive" />
  <LlmTaskLauncherDialog v-if="llmTaskLauncherActive" />
  <LlmToolResultDialog v-if="llmToolResultActive" />
  <MergeFilesDialog v-if="mergeFilesActive" />
  <MixedWorkValuesDialog v-if="mixedWorkValuesActive" />
  <OcrCleanupDialog v-if="ocrCleanupActive" />
  <PdfDraftRecordDialog v-if="pdfDraftRecordActive" />
  <RecordFieldEditorDialog v-if="recordFieldEditorActive" />
  <RecordHistoryDialog v-if="recordHistoryActive" />
  <RecordPreviewDialog v-if="recordPreviewActive" />
  <RemoveWorkDialog v-if="removeWorkActive" />
  <SeparateWorksDialog v-if="separateWorksActive" />
  <UpsertQueueDialog v-if="upsertQueueActive" />
  <WorkMetadataEditorDialog v-if="workMetadataEditorActive" />
  <WorkMetadataLlmDialog v-if="workMetadataLlmActive" />
  <WorkMetadataProposalDialog v-if="workMetadataProposalActive" />
</template>

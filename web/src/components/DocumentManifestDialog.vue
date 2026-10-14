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
import { useI18nStore } from "../stores/i18n";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
import UiDialog from "./ui/UiDialog.vue";

const props = withDefaults(
  defineProps<{
    manifest?: Record<string, unknown>;
    disabled?: boolean;
    affectedRecords?: number;
    mediaKind?: string;
    showReanalyze?: boolean;
    showImpactHeader?: boolean;
    showStructureFields?: boolean;
    title?: string;
    description?: string;
  }>(),
  {
    manifest: () => ({}),
    disabled: false,
    affectedRecords: 0,
    mediaKind: "",
    showReanalyze: true,
    showImpactHeader: true,
    showStructureFields: true,
    title: "",
    description: "",
  },
);
const emit = defineEmits<{ save: [changes: Record<string, unknown>]; reanalyze: []; close: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <UiDialog
    size="large"
    :title="props.title || i18n.t('pdf_corpus.edit_document_metadata')"
    :description="props.description || i18n.t('pdf_corpus.document_metadata_dialog_help')"
    :close-label="i18n.t('ui.close')"
    @close="emit('close')"
  >
    <DocumentManifestEditor
      :manifest="props.manifest"
      :disabled="props.disabled"
      :affected-records="props.affectedRecords"
      :media-kind="props.mediaKind"
      :show-reanalyze="props.showReanalyze"
      :show-impact-header="props.showImpactHeader"
      :show-structure-fields="props.showStructureFields"
      @save="emit('save', $event)"
      @reanalyze="emit('reanalyze')"
    />
  </UiDialog>
</template>

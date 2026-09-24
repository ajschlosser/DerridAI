<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
import UiDialog from "./ui/UiDialog.vue";

const props=withDefaults(defineProps<{manifest?:Record<string,unknown>;disabled?:boolean;affectedRecords?:number}>(),{manifest:()=>({}),disabled:false,affectedRecords:0});
const emit=defineEmits<{save:[changes:Record<string,unknown>];reanalyze:[];close:[]} >();
const i18n=useI18nStore();
</script>

<template>
  <UiDialog
    size="large"
    :title="i18n.t('pdf_corpus.edit_document_metadata')"
    :description="i18n.t('pdf_corpus.document_metadata_dialog_help')"
    :close-label="i18n.t('ui.close')"
    @close="emit('close')"
  >
    <DocumentManifestEditor
      :manifest="props.manifest"
      :disabled="props.disabled"
      :affected-records="props.affectedRecords"
      @save="emit('save',$event)"
      @reanalyze="emit('reanalyze')"
    />
  </UiDialog>
</template>

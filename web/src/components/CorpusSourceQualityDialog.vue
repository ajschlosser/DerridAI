<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
import type { ExtractionNoise } from "../domain/sourceQuality";
import UiDialog from "./ui/UiDialog.vue";
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";
import AppIcon from "./AppIcon.vue";

defineProps<{
  open?: boolean;
  extractionNoise?: ExtractionNoise | null;
  issues?: Array<Record<string, unknown>>;
}>();
const emit = defineEmits<{ close: []; editText: []; openSource: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <UiDialog
    v-if="open"
    size="large"
    :title="i18n.t('pdf_corpus.source_issue_title', 'Source extraction issue')"
    :description="
      i18n.t(
        'pdf_corpus.source_warning_ingest_help',
        'Extraction quality was scored when this PDF was loaded. Review the findings, then continue; the warning stays on affected records as an icon.',
      )
    "
    :close-label="i18n.t('ui.close', 'Close')"
    @close="emit('close')"
  >
    <div class="quality-dialog">
      <div v-if="extractionNoise" class="quality-summary" role="status">
        <AppIcon name="warning" />
        <p>
          {{
            i18n.tf(
              "pdf_corpus.source_warning_ingest_summary",
              "{unusable} of {pages} page(s) look unusable · median noise {median}% · threshold {threshold}%",
              {
                unusable: Number(extractionNoise.unusable_page_count || 0),
                pages: Number(extractionNoise.page_count || 0),
                median:
                  extractionNoise.median_noise == null
                    ? "—"
                    : Math.round(Number(extractionNoise.median_noise)),
                threshold: Math.round(Number(extractionNoise.threshold || 45)),
              },
            )
          }}
        </p>
      </div>
      <CorpusSourceIssuePanel
        v-if="issues?.length"
        :issues="issues"
        interactive
        @edit-text="emit('editText')"
        @open-source="emit('openSource')"
      />
    </div>
    <template #footer>
      <button type="button" class="btn primary" @click="emit('close')">
        {{ i18n.t("pdf_corpus.source_warning_acknowledge", "Continue with this source") }}
      </button>
    </template>
  </UiDialog>
</template>
<style scoped>
.quality-dialog {
  display: grid;
  gap: 14px;
}
.quality-summary {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.quality-summary svg {
  width: 22px;
  height: 22px;
  flex: none;
  margin-block-start: 2px;
}
.quality-summary p {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
}
</style>

<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { useI18nStore } from "../../stores/i18n";
import type {
  CorpusSetupSectionId,
  CorpusSetupSectionState,
} from "../../features/corpus-builder/domain/setupState";
import CorpusSetupSection from "./CorpusSetupSection.vue";

const props = defineProps<{
  sections: CorpusSetupSectionState[];
  /** The one section whose controls are open; empty when all are collapsed. */
  expanded: CorpusSetupSectionId | "";
  disabledSections?: CorpusSetupSectionId[];
}>();
defineEmits<{ toggle: [section: CorpusSetupSectionId] }>();
const i18n = useI18nStore();
const titleKeys: Record<CorpusSetupSectionId, [string, string]> = {
  source: ["pdf_corpus.configure_source", "pdf_corpus.source_setup_help"],
  structure: ["pdf_corpus.configure_structure", "pdf_corpus.structure_before_build_help"],
  metadata: ["pdf_corpus.configure_metadata", "pdf_corpus.setup.help.metadata"],
  enrichment: ["pdf_corpus.configure_enrichment", "pdf_corpus.setup.help.enrichment"],
  advanced: ["pdf_corpus.configure_advanced", "pdf_corpus.setup.help.advanced"],
};
</script>

<template>
  <section
    class="corpus-setup-workspace corpus-workspace-surface"
    :aria-labelledby="'pdf-corpus-config-title'"
  >
    <h2 id="pdf-corpus-config-title" class="sr-only">
      {{ i18n.t("pdf_corpus.build_configuration") }}
    </h2>
    <div class="corpus-setup-layout">
      <div class="corpus-setup-sections">
        <CorpusSetupSection
          v-for="section in sections"
          :id="section.id"
          :key="section.id"
          :title="i18n.t(titleKeys[section.id][0])"
          :description="i18n.t(titleKeys[section.id][1])"
          :state="section.state"
          :summary="section.summary"
          :expanded="expanded === section.id"
          :disabled="props.disabledSections?.includes(section.id)"
          @toggle="$emit('toggle', section.id)"
        >
          <slot :name="section.id"></slot>
        </CorpusSetupSection>
      </div>
      <aside class="corpus-setup-plan">
        <slot name="footer"></slot>
      </aside>
    </div>
  </section>
</template>

<style scoped>
/* Structure-section content is slotted from the parent, so it is styled from here. */
.corpus-setup-workspace :deep(.setup-continue) {
  display: flex;
  justify-content: flex-end;
}
.corpus-setup-workspace :deep(.document-structure-config) {
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.corpus-setup-workspace :deep(.setup-disclosure) {
  overflow: visible;
  border-top: 1px solid var(--border-subtle);
}
.corpus-setup-workspace :deep(.setup-disclosure > summary) {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 54px;
  padding: var(--space-3) 0;
}
.corpus-setup-workspace :deep(.setup-disclosure > summary::-webkit-details-marker) {
  display: none;
}
.corpus-setup-workspace :deep(.setup-disclosure > summary > span:last-child) {
  display: grid;
  gap: 2px;
}
.corpus-setup-workspace :deep(.setup-disclosure > summary b) {
  font-size: 0.9375rem;
}
.corpus-setup-workspace :deep(.setup-disclosure > summary small) {
  color: var(--text-secondary);
  font-size: 0.8125rem !important;
  font-weight: 500;
}
.corpus-setup-workspace :deep(.setup-disclosure[open] > summary) {
  border-bottom: 1px solid var(--border-subtle);
  background: transparent;
}
.corpus-setup-workspace :deep(.setup-disclosure-body) {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0 var(--space-5);
}

.corpus-setup-workspace {
  display: grid;
  gap: var(--space-4);
}
.corpus-setup-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(19rem, 23rem);
  gap: var(--space-5);
  align-items: start;
}
.corpus-setup-sections {
  display: grid;
  min-width: 0;
  gap: var(--space-3);
}
.corpus-setup-plan {
  position: sticky;
  top: calc(var(--ref-topbar, 60px) + var(--space-4));
  min-width: 0;
}
@media (max-width: 1100px) {
  .corpus-setup-layout {
    grid-template-columns: 1fr;
  }
  .corpus-setup-plan {
    position: static;
  }
}
</style>

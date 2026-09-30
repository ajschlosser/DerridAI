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
    <slot name="footer"></slot>
  </section>
</template>

<style scoped>
.corpus-setup-workspace {
  display: grid;
  gap: var(--space-4);
}
.corpus-setup-sections {
  display: grid;
  gap: var(--space-3);
}
</style>

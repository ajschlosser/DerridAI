<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
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
  /** Set when a build already exists: edits here configure the next build, never the existing one. */
  existingBuildName?: string;
}>();
defineEmits<{ toggle: [section: CorpusSetupSectionId] }>();
const i18n = useI18nStore();
const requiredSections = computed(() =>
  props.sections.filter((section) => section.id !== "advanced"),
);
const completedRequired = computed(
  () => requiredSections.value.filter((section) => section.state === "complete").length,
);
const setupWarnings = computed(
  () => requiredSections.value.filter((section) => section.state === "warning").length,
);
function stepNumber(section: CorpusSetupSectionState) {
  if (section.id === "advanced") return undefined;
  return requiredSections.value.findIndex((item) => item.id === section.id) + 1;
}
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
    <header class="corpus-setup-overview">
      <div>
        <h2 id="pdf-corpus-config-title">{{ i18n.t("pdf_corpus.build_configuration") }}</h2>
        <p v-if="setupWarnings" class="corpus-setup-attention">
          {{ i18n.t("pdf_corpus.attention_required") }} ·
          {{ i18n.tf("pdf_corpus.readiness.note_count", { count: setupWarnings }) }}
        </p>
      </div>
      <div
        class="corpus-setup-progress"
        role="group"
        :aria-label="i18n.t('pdf_corpus.build_configuration')"
      >
        <span>
          {{ completedRequired }} / {{ requiredSections.length }}
          {{ i18n.t("pdf_corpus.complete") }}
        </span>
        <progress
          :aria-label="i18n.t('pdf_corpus.build_configuration')"
          :max="requiredSections.length"
          :value="completedRequired"
        ></progress>
      </div>
    </header>
    <p v-if="props.existingBuildName" class="corpus-setup-next-build" role="note">
      {{ i18n.tf("pdf_corpus.setup.applies_to_next_build", { build: props.existingBuildName }) }}
    </p>
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
          :step="stepNumber(section)"
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
.corpus-setup-overview {
  display: flex;
  justify-content: space-between;
  gap: var(--space-5);
  align-items: end;
}
.corpus-setup-overview h2 {
  margin: 0;
  font-size: var(--fs-xl);
}
.corpus-setup-attention {
  margin: var(--space-1) 0 0;
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.corpus-setup-progress {
  min-width: min(17rem, 40%);
  display: grid;
  gap: var(--space-1);
}
.corpus-setup-progress span {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  text-align: end;
}
.corpus-setup-progress progress {
  width: 100%;
  height: 0.4rem;
  border: 0;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-subtle);
}
.corpus-setup-progress progress::-webkit-progress-bar {
  background: var(--surface-subtle);
}
.corpus-setup-progress progress::-webkit-progress-value {
  background: var(--accent-fg);
}
.corpus-setup-progress progress::-moz-progress-bar {
  background: var(--accent-fg);
}
.corpus-setup-next-build {
  margin: 0 0 var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-info-border);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
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
  .corpus-setup-overview {
    align-items: stretch;
    flex-direction: column;
    gap: var(--space-3);
  }
  .corpus-setup-progress {
    width: 100%;
    min-width: 0;
  }
  .corpus-setup-progress span {
    text-align: start;
  }
  .corpus-setup-layout {
    grid-template-columns: 1fr;
  }
  .corpus-setup-plan {
    position: static;
  }
}
</style>

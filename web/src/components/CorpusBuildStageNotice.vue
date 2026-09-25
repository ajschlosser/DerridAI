<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";

defineProps<{ stage?: string }>();
const i18n = useI18nStore();
</script>

<template>
  <section class="build-stage-active" role="status" aria-live="polite">
    <span class="eyebrow">{{ i18n.t("pdf_corpus.building_records") }}</span>
    <h3>{{ i18n.t("pdf_corpus.building_records_title") }}</h3>
    <p>{{ i18n.t("pdf_corpus.building_records_help") }}</p>
    <small v-if="stage" class="stage-detail">
      <span class="stage-label">{{ i18n.t("pdf_corpus.current_stage") }}:</span>
      <span class="stage-value">{{ stage }}</span>
    </small>
  </section>
</template>

<style scoped>
.build-stage-active {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
  color: var(--text-primary);
}

.eyebrow {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-weight: var(--fw-bold);
}

.build-stage-active h3 {
  margin: 0;
  font-size: var(--fs-base);
  line-height: var(--lh-tight);
}

.build-stage-active p {
  margin: 0;
  max-width: var(--measure);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
  color: var(--text-secondary);
}

.stage-detail {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
  color: var(--text-secondary);
}

.stage-label {
  font-weight: var(--fw-semibold);
}

.stage-value {
  overflow-wrap: anywhere;
}
</style>

<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

const props = withDefaults(
  defineProps<{
    sourceFilename?: string;
    model?: string | null;
    buildId?: string;
    accepted?: number;
    reviewable?: number;
    remaining?: number;
    issues?: number;
    focusDisabled?: boolean;
  }>(),
  {
    sourceFilename: "",
    model: "",
    buildId: "",
    accepted: 0,
    reviewable: 0,
    remaining: 0,
    issues: 0,
    focusDisabled: false,
  },
);

const emit = defineEmits<{ focus: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <section class="review-session" aria-labelledby="review-session-title">
    <div class="review-identity">
      <span class="eyebrow">{{ i18n.t("pdf_corpus.review_mode") }}</span>
      <b id="review-session-title">{{ props.sourceFilename }}</b>
      <small>
        {{ props.model || i18n.t("pdf_corpus.provider_default") }}
        <template v-if="props.buildId"> · {{ props.buildId }}</template>
      </small>
    </div>

    <dl class="review-stats">
      <div>
        <dd>{{ props.accepted }}</dd>
        <dt>{{ i18n.t("pdf_corpus.accepted_label") }}</dt>
      </div>
      <div>
        <dd>{{ props.reviewable }}</dd>
        <dt>{{ i18n.t("pdf_corpus.queue_ready") }}</dt>
      </div>
      <div>
        <dd>{{ props.remaining }}</dd>
        <dt>{{ i18n.t("pdf_corpus.remaining") }}</dt>
      </div>
      <div>
        <dd>{{ props.issues }}</dd>
        <dt>{{ i18n.t("pdf_corpus.need_attention") }}</dt>
      </div>
    </dl>

    <UiButton
      size="small"
      :label="i18n.t('pdf_corpus.focus_view')"
      :disabled="props.focusDisabled"
      @click="emit('focus')"
    />
  </section>
</template>

<style scoped>
.review-session {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}

.review-identity {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}

.review-identity b {
  font-size: var(--fs-base);
  overflow-wrap: anywhere;
}

.review-identity small {
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}

.eyebrow {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-weight: var(--fw-bold);
}

.review-stats {
  display: flex;
  gap: var(--space-1);
  margin: 0;
}

.review-stats > div {
  min-width: 74px;
  padding: var(--space-2);
  text-align: center;
  border-inline-start: 1px solid var(--border-subtle);
}

.review-stats dd {
  margin: 0;
  font-size: var(--fs-md);
  font-weight: var(--fw-bold);
  font-variant-numeric: tabular-nums;
}

.review-stats dt {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: var(--lh-tight);
}

@media (max-width: 1100px) {
  .review-session {
    grid-template-columns: 1fr auto;
  }

  .review-stats {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }

  .review-stats > div:first-child {
    border-inline-start: 0;
  }
}

@media (max-width: 700px) {
  .review-session {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }

  .review-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .review-stats > div {
    min-width: 0;
    border: 1px solid var(--border-subtle);
    background: var(--surface-inset);
    border-radius: var(--radius-control);
  }
}
</style>

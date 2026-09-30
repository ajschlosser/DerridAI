<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
import AppIcon from "./AppIcon.vue";
import UiButton from "./ui/UiButton.vue";
import UiDialog from "./ui/UiDialog.vue";

withDefaults(
  defineProps<{
    open: boolean;
    busy?: boolean;
    pendingRecords?: number;
    unresolvedFields?: number;
  }>(),
  {
    busy: false,
    pendingRecords: 0,
    unresolvedFields: 0,
  },
);

const emit = defineEmits<{ close: []; confirm: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <UiDialog
    :open="open"
    size="medium"
    :title="i18n.t('pdf_corpus.accept_unreviewed_dialog_title')"
    :description="i18n.t('pdf_corpus.accept_unreviewed_dialog_help')"
    :close-label="i18n.t('ui.close')"
    @close="emit('close')"
  >
    <div class="publish-review">
      <section class="publish-review__summary" aria-labelledby="publish-review-summary-title">
        <div class="publish-review__icon" aria-hidden="true">
          <AppIcon name="warning" />
        </div>
        <div>
          <h3 id="publish-review-summary-title">
            {{ i18n.t("pdf_corpus.accept_unreviewed_summary_title") }}
          </h3>
          <p>{{ i18n.t("pdf_corpus.accept_unreviewed_summary_help") }}</p>
        </div>
      </section>

      <dl class="publish-review__stats">
        <div>
          <dt>{{ i18n.t("pdf_corpus.pending_review") }}</dt>
          <dd>{{ pendingRecords }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("pdf_corpus.unresolved_metadata") }}</dt>
          <dd>{{ unresolvedFields }}</dd>
        </div>
      </dl>

      <div class="publish-review__details">
        <h3>{{ i18n.t("pdf_corpus.accept_unreviewed_what_happens") }}</h3>
        <ul>
          <li>{{ i18n.t("pdf_corpus.accept_unreviewed_scope") }}</li>
          <li>{{ i18n.t("pdf_corpus.accept_unreviewed_preserves") }}</li>
          <li>{{ i18n.t("pdf_corpus.accept_unreviewed_conformance") }}</li>
        </ul>
      </div>
    </div>

    <template #footer>
      <p class="publish-review__footer-note">
        {{ i18n.t("pdf_corpus.accept_unreviewed_snapshot_only") }}
      </p>
      <div class="publish-review__actions">
        <UiButton
          :label="i18n.t('ui.cancel')"
          :disabled="busy"
          @click="emit('close')"
        />
        <UiButton
          variant="primary"
          :label="i18n.t('pdf_corpus.accept_unreviewed_confirm_action')"
          :disabled="busy"
          @click="emit('confirm')"
        />
      </div>
    </template>
  </UiDialog>
</template>

<style scoped>
.publish-review {
  display: grid;
  gap: 18px;
}
.publish-review__summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 14px 16px;
  border: 1px solid var(--tone-warning-border);
  border-radius: var(--radius-card);
  background: var(--tone-warning-bg);
}
.publish-review__icon {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  color: var(--tone-warning-fg);
}
.publish-review__icon :deep(svg) {
  width: 18px;
  height: 18px;
}
.publish-review h3,
.publish-review p {
  margin: 0;
}
.publish-review h3 {
  font-size: 0.9375rem;
}
.publish-review p,
.publish-review li {
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.5;
}
.publish-review__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}
.publish-review__stats > div {
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
}
.publish-review__stats dt {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 700;
}
.publish-review__stats dd {
  margin: 3px 0 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  font-weight: 750;
}
.publish-review__details {
  display: grid;
  gap: 8px;
}
.publish-review__details ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}
.publish-review__footer-note {
  max-width: 42ch;
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: 1.4;
}
.publish-review__actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-left: auto;
}
@media (max-width: 620px) {
  .publish-review__stats {
    grid-template-columns: 1fr;
  }
  .publish-review__actions {
    width: 100%;
    margin-left: 0;
  }
  .publish-review__actions :deep(.ui-button-wrap) {
    flex: 1 1 0;
  }
  .publish-review__actions :deep(.ui-button) {
    width: 100%;
  }
}
</style>

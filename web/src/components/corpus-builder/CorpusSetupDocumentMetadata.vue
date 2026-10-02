<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import DocumentManifestDialog from "../DocumentManifestDialog.vue";
import UiButton from "../ui/UiButton.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const props = withDefaults(
  defineProps<{
    manifest?: Record<string, unknown>;
    mediaKind?: string;
    missingRequiredCount?: number;
    reviewerOverrideCount?: number;
    disabled?: boolean;
  }>(),
  {
    manifest: () => ({}),
    mediaKind: "",
    missingRequiredCount: 0,
    reviewerOverrideCount: 0,
    disabled: false,
  },
);
const emit = defineEmits<{ save: [changes: Record<string, unknown>] }>();
const i18n = useI18nStore();
const open = ref(false);

function value(name: string): string {
  return String(props.manifest?.[name] ?? "").trim();
}
const title = computed(
  () => value("title") || i18n.t("pdf_corpus.setup.document_metadata_title_missing"),
);
const author = computed(() => value("document_author") || i18n.t("pdf_corpus.metadata_unset"));
const translator = computed(() => value("translator") || i18n.t("pdf_corpus.metadata_unset"));
const language = computed(() => {
  const current = value("language");
  const original = value("original_language");
  if (!current && !original) return i18n.t("pdf_corpus.metadata_unset");
  if (current && original && current !== original) return `${current} · ${original}`;
  return current || original;
});
const publication = computed(() => {
  const bits = [value("publisher"), value("publication_place"), value("publication_year")].filter(
    Boolean,
  );
  return bits.length ? bits.join(" · ") : i18n.t("pdf_corpus.metadata_unset");
});
const detectedCount = computed(() => {
  const ingest = props.manifest?.deterministic_ingest as
    | { applied?: Record<string, unknown> }
    | undefined;
  return Object.keys(ingest?.applied || {}).length;
});
const statusTone = computed(() => (props.missingRequiredCount > 0 ? "warning" : "success"));
const statusLabel = computed(() =>
  props.missingRequiredCount > 0
    ? i18n.tf("pdf_corpus.setup.document_metadata_missing", {
        count: props.missingRequiredCount,
      })
    : i18n.t("pdf_corpus.setup.document_metadata_ready"),
);
</script>

<template>
  <section class="setup-document-metadata" aria-labelledby="setup-document-metadata-title">
    <header class="setup-document-metadata-header">
      <div class="setup-document-metadata-heading">
        <span class="eyebrow">{{ i18n.t("pdf_corpus.setup.document_metadata") }}</span>
        <h4 id="setup-document-metadata-title">{{ title }}</h4>
        <p>{{ i18n.t("pdf_corpus.setup.document_metadata_help") }}</p>
      </div>
      <UiStatusBadge :tone="statusTone" :label="statusLabel" />
    </header>

    <dl class="setup-document-metadata-facts">
      <div>
        <dt>{{ i18n.t("pdf_corpus.manifest_author") }}</dt>
        <dd>{{ author }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.setup.document_metadata_publication") }}</dt>
        <dd>{{ publication }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.manifest_language") }}</dt>
        <dd>{{ language }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.manifest_translator") }}</dt>
        <dd>{{ translator }}</dd>
      </div>
    </dl>

    <footer class="setup-document-metadata-footer">
      <div class="setup-document-metadata-provenance" aria-live="polite">
        <span v-if="detectedCount">
          {{
            i18n.tf("pdf_corpus.setup.document_metadata_detected", {
              count: detectedCount,
            })
          }}
        </span>
        <span v-if="props.reviewerOverrideCount">
          {{
            i18n.tf("pdf_corpus.setup.document_metadata_reviewed", {
              count: props.reviewerOverrideCount,
            })
          }}
        </span>
        <span v-if="!detectedCount && !props.reviewerOverrideCount">
          {{ i18n.t("pdf_corpus.setup.document_metadata_no_detected") }}
        </span>
      </div>
      <UiButton
        variant="soft"
        :label="i18n.t('pdf_corpus.setup.document_metadata_review')"
        :disabled="props.disabled"
        @click="open = true"
      />
    </footer>

    <DocumentManifestDialog
      v-if="open"
      :manifest="props.manifest"
      :media-kind="props.mediaKind"
      :disabled="props.disabled"
      :show-reanalyze="false"
      :show-impact-header="false"
      :show-structure-fields="false"
      :title="i18n.t('pdf_corpus.setup.document_metadata_dialog_title')"
      :description="i18n.t('pdf_corpus.setup.document_metadata_dialog_help')"
      @save="emit('save', $event)"
      @close="open = false"
    />
  </section>
</template>

<style scoped>
.setup-document-metadata {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.setup-document-metadata-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
}
.setup-document-metadata-heading {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
}
.eyebrow {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.setup-document-metadata h4 {
  margin: 0;
  font-size: var(--fs-lg);
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.setup-document-metadata-heading p {
  max-width: 72ch;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.setup-document-metadata-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}
.setup-document-metadata-facts > div {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.setup-document-metadata-facts dt {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.setup-document-metadata-facts dd {
  min-width: 0;
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.setup-document-metadata-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.setup-document-metadata-provenance {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: 1.4;
}
@media (max-width: 700px) {
  .setup-document-metadata {
    padding: var(--space-4);
  }
  .setup-document-metadata-header,
  .setup-document-metadata-footer {
    align-items: stretch;
    flex-direction: column;
  }
  .setup-document-metadata-facts {
    grid-template-columns: 1fr;
  }
}
</style>

<!-- Copyright © 2026 Aaron John Schlosser, PhD. AGPL-3.0-or-later -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { PdfAsset } from "../api/corpus";
import { formatSourcePageSelection, parseSourcePageSelection } from "../domain/sourcePageScope";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import UiField from "./ui/UiField.vue";
import UiInput from "./ui/UiInput.vue";

defineOptions({ name: "SourcePageScopeControl" });

const props = withDefaults(
  defineProps<{
    pageCount: number;
    pageDetection?: PdfAsset["page_number_detection"];
    disabled?: boolean;
  }>(),
  { pageDetection: undefined, disabled: false },
);
const pages = defineModel<number[]>({ default: () => [] });
const emit = defineEmits<{ validity: [valid: boolean] }>();
const i18n = useI18nStore();
const draft = ref(formatSourcePageSelection(pages.value));
let locallyApplied = "";

watch(
  () => pages.value,
  (value) => {
    const signature = value.join(",");
    if (signature === locallyApplied) {
      locallyApplied = "";
      return;
    }
    draft.value = formatSourcePageSelection(value);
  },
  { deep: true },
);
watch(
  () => props.pageCount,
  () => {
    const result = parseSourcePageSelection(draft.value, props.pageCount);
    if (result.error) {
      draft.value = formatSourcePageSelection(pages.value);
    }
  },
);

const parsed = computed(() => parseSourcePageSelection(draft.value, props.pageCount));
watch(
  () => parsed.value.error,
  (value) => emit("validity", !value),
  { immediate: true },
);
const error = computed(() =>
  parsed.value.error ? i18n.t("pdf_corpus.source_scope_invalid", parsed.value.error) : "",
);
const selectedCount = computed(() => pages.value.length || Math.max(0, props.pageCount));
const summary = computed(() =>
  pages.value.length
    ? `${i18n.t("pdf_corpus.source_scope_selected_label", "Pages selected")}: ${selectedCount.value}`
    : `${i18n.t("pdf_corpus.source_scope_all_label", "All pages")}: ${selectedCount.value}`,
);
const provenance = computed(() => {
  const detection = props.pageDetection;
  if (!detection) {
    return i18n.t(
      "pdf_corpus.source_scope_physical_help",
      "Selections use the source's extracted page order.",
    );
  }
  if (detection.status === "detected") {
    return i18n.t(
      "pdf_corpus.source_scope_detected_help",
      "Page boundaries were detected from the document. The selection uses those extracted pages.",
    );
  }
  if (detection.status === "estimated") {
    return i18n.t(
      "pdf_corpus.source_scope_estimated_help",
      "These pages are estimated from the text stream. The build retains that provenance.",
    );
  }
  return i18n.t(
    "pdf_corpus.source_scope_logical_help",
    "The selection uses the source units currently represented as pages.",
  );
});

function update(value: string) {
  draft.value = value;
  const result = parseSourcePageSelection(value, props.pageCount);
  if (!result.error) {
    locallyApplied = result.pages.join(",");
    pages.value = result.pages;
  }
}

function useAllPages() {
  draft.value = "";
  locallyApplied = "";
  pages.value = [];
}
</script>

<template>
  <section class="source-scope" aria-labelledby="source-scope-title">
    <header>
      <div>
        <h3 id="source-scope-title">
          {{ i18n.t("pdf_corpus.source_scope_title", "Pages included in this build") }}
        </h3>
        <p>{{ provenance }}</p>
      </div>
      <span class="scope-summary" aria-live="polite">{{ summary }}</span>
    </header>
    <div class="scope-controls">
      <UiField
        control-id="corpus-source-page-scope"
        :label="i18n.t('pdf_corpus.source_scope_label', 'Page range or specific pages')"
        :hint="
          i18n.t(
            'pdf_corpus.source_scope_help',
            'Examples: 1-25 · 1, 4, 7 · 1-12, 17, 21-35. Leave blank to include every page.',
          )
        "
        :error="error"
        wide
      >
        <template #default="{ describedby, invalid, controlId }">
          <UiInput
            :id="controlId"
            :model-value="draft"
            :aria-describedby="describedby"
            :invalid="invalid"
            :disabled="disabled"
            autocomplete="off"
            :placeholder="i18n.t('pdf_corpus.source_scope_placeholder', 'All pages')"
            @update:model-value="update(String($event))"
          />
        </template>
      </UiField>
      <UiButton
        variant="ghost"
        :label="i18n.t('pdf_corpus.source_scope_reset', 'Use all pages')"
        :disabled="disabled || !pages.length"
        @click="useAllPages"
      />
    </div>
  </section>
</template>

<style scoped>
.source-scope {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.source-scope header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.source-scope h3,
.source-scope p {
  margin: 0;
}
.source-scope h3 {
  font-size: var(--fs-md);
}
.source-scope p {
  max-width: 72ch;
  margin-top: var(--space-1);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.scope-summary {
  flex: none;
  padding: 4px 9px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  background: var(--surface-inset);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.scope-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: end;
}
@media (max-width: 700px) {
  .source-scope header,
  .scope-controls {
    display: grid;
    grid-template-columns: 1fr;
  }
  .scope-summary {
    justify-self: start;
  }
}
</style>

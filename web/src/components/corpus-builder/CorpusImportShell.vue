<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import UiDialog from "../ui/UiDialog.vue";

type ImportMode = "library" | "author";

const props = withDefaults(
  defineProps<{ open: boolean; defaultMode?: ImportMode; disabled?: boolean }>(),
  { defaultMode: "library", disabled: false },
);
const emit = defineEmits<{ close: []; choose: [mode: ImportMode] }>();
const i18n = useI18nStore();
const mode = ref<ImportMode>(props.defaultMode);

watch(
  () => [props.open, props.defaultMode] as const,
  ([open, nextMode]) => {
    if (open) mode.value = nextMode;
  },
);

function choose(next: ImportMode) {
  if (props.disabled) return;
  emit("choose", next);
}
</script>

<template>
  <UiDialog
    :open="open"
    :title="i18n.t('pdf_corpus.import_shell.title')"
    :description="i18n.t('pdf_corpus.import_shell.description')"
    :close-label="i18n.t('common.close')"
    size="medium"
    @close="emit('close')"
  >
    <div class="import-shell">
      <div class="import-tabs" role="tablist" :aria-label="i18n.t('pdf_corpus.import_shell.title')">
        <button
          type="button"
          role="tab"
          class="import-tab"
          :aria-selected="mode === 'library'"
          @click="mode = 'library'"
        >
          <AppIcon name="books" />{{ i18n.t("pdf_corpus.search_library") }}
        </button>
        <button
          type="button"
          role="tab"
          class="import-tab"
          :aria-selected="mode === 'author'"
          @click="mode = 'author'"
        >
          <AppIcon name="users" />{{ i18n.t("capture.path_title") }}
        </button>
      </div>
      <section v-if="mode === 'library'" class="import-panel" role="tabpanel">
        <h3>{{ i18n.t("pdf_corpus.import_shell.library_title") }}</h3>
        <p>{{ i18n.t("pdf_corpus.import_shell.library_help") }}</p>
        <button
          type="button"
          class="btn primary"
          data-action="open-library"
          :disabled="disabled"
          @click="choose('library')"
        >
          {{ i18n.t("pdf_corpus.import_shell.open_library") }}
        </button>
      </section>
      <section v-else class="import-panel" role="tabpanel">
        <h3>{{ i18n.t("pdf_corpus.import_shell.author_title") }}</h3>
        <p>{{ i18n.t("pdf_corpus.import_shell.author_help") }}</p>
        <button
          type="button"
          class="btn primary"
          data-action="open-author"
          :disabled="disabled"
          @click="choose('author')"
        >
          {{ i18n.t("pdf_corpus.import_shell.open_author") }}
        </button>
      </section>
    </div>
  </UiDialog>
</template>

<style scoped>
.import-shell {
  display: grid;
  gap: 18px;
}
.import-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.import-tab {
  display: inline-flex;
  gap: 7px;
  align-items: center;
  padding: 9px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  color: var(--text-primary);
  background: var(--surface-card);
  cursor: pointer;
}
.import-tab[aria-selected="true"] {
  border-color: var(--accent-border);
  background: var(--surface-selected);
}
.import-panel {
  display: grid;
  gap: 10px;
}
.import-panel h3,
.import-panel p {
  margin: 0;
}
.import-panel p {
  color: var(--text-secondary);
}
</style>

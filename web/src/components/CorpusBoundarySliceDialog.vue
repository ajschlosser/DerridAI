<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiDialog from "./ui/UiDialog.vue";
const props = defineProps<{
  text: string;
  canPrevious: boolean;
  canNext: boolean;
  busy?: boolean;
}>();
const emit = defineEmits<{
  close: [];
  split: [offset: number];
  create: [
    start: number,
    end: number,
    left: "distinct" | "merge_prior",
    right: "distinct" | "merge_next",
  ];
}>();
const i18n = useI18nStore();
const textarea = ref<HTMLTextAreaElement | null>(null);
// A caret (start === end) chooses a split point; a range chooses text for a new record.
const start = ref(0);
const end = ref(0);
const left = ref<"distinct" | "merge_prior">("distinct");
const right = ref<"distinct" | "merge_next">("distinct");
const hasSelection = computed(() => end.value > start.value);
const before = computed(() => props.text.slice(0, start.value).trim());
const selected = computed(() => props.text.slice(start.value, end.value).trim());
const after = computed(() => props.text.slice(end.value).trim());
const wholeText = computed(() => hasSelection.value && !before.value && !after.value);
const canCreate = computed(
  () =>
    hasSelection.value &&
    !!selected.value &&
    !wholeText.value &&
    !(before.value && left.value === "merge_prior" && !props.canPrevious) &&
    !(after.value && right.value === "merge_next" && !props.canNext),
);
const canSplit = computed(
  () =>
    !hasSelection.value &&
    start.value > 0 &&
    start.value < props.text.length &&
    !!before.value &&
    !!after.value,
);
function capture() {
  const el = textarea.value;
  if (!el) return;
  start.value = Math.min(el.selectionStart || 0, el.selectionEnd || 0);
  end.value = Math.max(el.selectionStart || 0, el.selectionEnd || 0);
}
function create() {
  if (!canCreate.value) return;
  emit(
    "create",
    start.value,
    end.value,
    before.value ? left.value : "distinct",
    after.value ? right.value : "distinct",
  );
}
function split() {
  if (canSplit.value) emit("split", start.value);
}
watch(
  () => props.text,
  () => {
    start.value = end.value = Math.floor(props.text.length / 2);
    left.value = "distinct";
    right.value = "distinct";
    void nextTick(() => {
      textarea.value?.focus();
      textarea.value?.setSelectionRange(start.value, end.value);
    });
  },
  { immediate: true },
);
</script>
<template>
  <UiDialog
    :open="true"
    size="xlarge"
    :title="i18n.t('pdf_corpus.slice_record')"
    :description="i18n.t('pdf_corpus.slice_record_help')"
    :close-label="i18n.t('ui.close')"
    @close="emit('close')"
    ><label class="slice-label"
      ><span>{{ i18n.t("pdf_corpus.slice_point") }}</span
      ><textarea
        ref="textarea"
        :value="text"
        readonly
        aria-describedby="slice-instructions"
        @click="capture"
        @keyup="capture"
        @select="capture"
        @mouseup="capture"
      ></textarea>
    </label>
    <p id="slice-instructions" class="instructions">
      {{ i18n.t("pdf_corpus.slice_point_help") }}
    </p>
    <div class="preview-grid">
      <article>
        <b>{{ i18n.t("pdf_corpus.before_slice") }}</b>
        <p>{{ before || "—" }}</p>
      </article>
      <article v-if="hasSelection">
        <b>{{ i18n.t("pdf_corpus.selected_text") }}</b>
        <p>{{ selected || "—" }}</p>
      </article>
      <article>
        <b>{{ i18n.t("pdf_corpus.after_slice") }}</b>
        <p>{{ after || "—" }}</p>
      </article>
    </div>
    <div v-if="hasSelection" class="choices">
      <fieldset v-if="before">
        <legend>{{ i18n.t("pdf_corpus.leading_text_choice") }}</legend>
        <label
          ><input v-model="left" type="radio" name="slice-left" value="distinct" />
          {{ i18n.t("pdf_corpus.keep_separate") }}</label
        >
        <label
          ><input
            v-model="left"
            type="radio"
            name="slice-left"
            value="merge_prior"
            :disabled="!canPrevious"
          />
          {{ i18n.t("pdf_corpus.join_prior") }}</label
        >
      </fieldset>
      <fieldset v-if="after">
        <legend>{{ i18n.t("pdf_corpus.trailing_text_choice") }}</legend>
        <label
          ><input v-model="right" type="radio" name="slice-right" value="distinct" />
          {{ i18n.t("pdf_corpus.keep_separate") }}</label
        >
        <label
          ><input
            v-model="right"
            type="radio"
            name="slice-right"
            value="merge_next"
            :disabled="!canNext"
          />
          {{ i18n.t("pdf_corpus.join_next") }}</label
        >
      </fieldset>
    </div>
    <p v-if="wholeText" class="instructions" role="status">
      {{ i18n.t("pdf_corpus.selection_is_whole_record") }}
    </p>
    <template #footer
      ><div class="slice-actions">
        <button
          v-if="hasSelection"
          class="btn primary"
          type="button"
          :disabled="busy || !canCreate"
          @click="create"
        >
          {{ i18n.t("pdf_corpus.create_record_from_selection") }}</button
        ><button
          v-else
          class="btn primary"
          type="button"
          :disabled="busy || !canSplit"
          @click="split"
        >
          {{ i18n.t("pdf_corpus.split_at_caret") }}
        </button>
      </div></template
    ></UiDialog
  >
</template>
<style scoped>
.choices {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.choices fieldset {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.choices legend {
  font-weight: 750;
  padding: 0 4px;
}
.choices label {
  display: flex;
  gap: 8px;
  align-items: center;
}
.slice-label {
  display: grid;
  gap: 7px;
  font-weight: 750;
}
.slice-label textarea {
  width: 100%;
  min-height: 260px;
  resize: vertical;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--bg);
  color: var(--text);
  font:
    16px/1.65 Georgia,
    serif;
}
.instructions {
  margin: 0;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.preview-grid article {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 11px;
  background: var(--soft);
  min-width: 0;
}
.preview-grid p {
  margin: 7px 0 0;
  max-height: 140px;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 0.875rem;
  line-height: 1.5;
}
.slice-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}
:is(button, textarea, input):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 720px) {
  .preview-grid,
  .choices {
    grid-template-columns: 1fr;
  }
  .slice-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

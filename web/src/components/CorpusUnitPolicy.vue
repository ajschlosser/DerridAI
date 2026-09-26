<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import {
  corpusBuilderApi,
  type PdfAsset,
  type SourceUnitMode,
  type SourceUnitPolicy,
  type SourceUnitPreview,
} from "../api/corpus";
import { useI18nStore } from "../stores/i18n";

/**
 * How finely the source is divided into evidence units. Choosing a policy previews the result;
 * applying it creates a new version of the source (the original is kept).
 */
const props = defineProps<{ asset: PdfAsset; disabled?: boolean; busy?: boolean }>();
const emit = defineEmits<{ apply: [policy: SourceUnitPolicy] }>();
const i18n = useI18nStore();

const MODES: SourceUnitMode[] = ["default", "paragraph", "line", "sentence", "chars"];
const CHAR_PRESETS = [200, 500, 1000, 2000];
const current = computed<SourceUnitPolicy>(() => props.asset.unit_policy ?? { mode: "default" });
const mode = ref<SourceUnitMode>(current.value.mode);
const chars = ref<number>(current.value.chars ?? 500);
const preview = ref<SourceUnitPreview | null>(null);
const loading = ref(false);
const error = ref("");
let timer: number | null = null;
let sequence = 0;

const policy = computed<SourceUnitPolicy>(() =>
  mode.value === "chars" ? { mode: "chars", chars: Number(chars.value) } : { mode: mode.value },
);
const charsValid = computed(() => Number(chars.value) >= 60 && Number(chars.value) <= 20000);
const unchanged = computed(
  () =>
    current.value.mode === policy.value.mode &&
    (policy.value.mode !== "chars" || current.value.chars === policy.value.chars),
);

async function refresh() {
  if (mode.value === "chars" && !charsValid.value) return;
  const ticket = ++sequence;
  loading.value = true;
  error.value = "";
  try {
    // A preview is computed from the source blocks the API already holds; nothing is saved.
    const result = await corpusBuilderApi.previewUnitPolicy(
      props.asset.derived_from_asset_id || props.asset.asset_id,
      policy.value,
    );
    if (ticket === sequence) preview.value = result;
  } catch (cause) {
    if (ticket === sequence) {
      preview.value = null;
      error.value = cause instanceof Error ? cause.message : String(cause);
    }
  } finally {
    if (ticket === sequence) loading.value = false;
  }
}

function schedule() {
  if (timer !== null) window.clearTimeout(timer);
  timer = window.setTimeout(refresh, 250);
}
watch([mode, chars], schedule);
watch(
  () => props.asset.asset_id,
  () => {
    mode.value = current.value.mode;
    chars.value = current.value.chars ?? 500;
    preview.value = null;
    schedule();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  if (timer !== null) window.clearTimeout(timer);
});

function apply() {
  if (!unchanged.value && (mode.value !== "chars" || charsValid.value)) emit("apply", policy.value);
}
</script>

<template>
  <section class="unit-policy" aria-labelledby="unit-policy-title">
    <header class="unit-head">
      <div>
        <h4 id="unit-policy-title">{{ i18n.t("pdf_corpus.units_title") }}</h4>
        <p>{{ i18n.t("pdf_corpus.units_help") }}</p>
      </div>
      <span v-if="!unchanged" class="unit-pending">{{ i18n.t("pdf_corpus.units_unapplied") }}</span>
    </header>

    <fieldset class="unit-modes" :disabled="disabled">
      <legend class="sr-only">{{ i18n.t("pdf_corpus.units_title") }}</legend>
      <label
        v-for="option in MODES"
        :key="option"
        class="unit-mode"
        :class="{ 'is-selected': mode === option }"
      >
        <input v-model="mode" type="radio" name="unit-policy" :value="option" />
        <svg class="unit-glyph" viewBox="0 0 64 40" aria-hidden="true" focusable="false">
          <template v-if="option === 'default'">
            <rect x="4" y="6" width="56" height="6" rx="3" />
            <rect x="4" y="17" width="56" height="6" rx="3" />
            <rect x="4" y="28" width="34" height="6" rx="3" />
          </template>
          <template v-else-if="option === 'paragraph'">
            <rect x="4" y="4" width="56" height="8" rx="3" />
            <rect x="4" y="16" width="56" height="4" rx="2" />
            <rect x="4" y="28" width="56" height="8" rx="3" />
          </template>
          <template v-else-if="option === 'line'">
            <rect x="4" y="5" width="56" height="5" rx="2.5" />
            <rect x="4" y="14" width="56" height="5" rx="2.5" />
            <rect x="4" y="23" width="56" height="5" rx="2.5" />
            <rect x="4" y="32" width="40" height="5" rx="2.5" />
          </template>
          <template v-else-if="option === 'sentence'">
            <rect x="4" y="8" width="20" height="6" rx="3" />
            <rect x="28" y="8" width="32" height="6" rx="3" />
            <rect x="4" y="19" width="34" height="6" rx="3" />
            <rect x="42" y="19" width="18" height="6" rx="3" />
            <rect x="4" y="30" width="26" height="6" rx="3" />
          </template>
          <template v-else>
            <rect x="4" y="6" width="26" height="6" rx="3" />
            <rect x="34" y="6" width="26" height="6" rx="3" />
            <rect x="4" y="17" width="26" height="6" rx="3" />
            <rect x="34" y="17" width="26" height="6" rx="3" />
            <rect x="4" y="28" width="26" height="6" rx="3" />
          </template>
        </svg>
        <span class="unit-copy">
          <strong>{{ i18n.t(`pdf_corpus.units_mode_${option}`) }}</strong>
          <small>{{ i18n.t(`pdf_corpus.units_mode_${option}_help`) }}</small>
        </span>
      </label>
    </fieldset>

    <div v-if="mode === 'chars'" class="unit-chars">
      <label for="unit-chars-input">{{ i18n.t("pdf_corpus.units_chars_label") }}</label>
      <input
        id="unit-chars-input"
        v-model.number="chars"
        class="control"
        type="number"
        min="60"
        max="20000"
        step="50"
        :disabled="disabled"
        :aria-invalid="!charsValid"
      />
      <div class="unit-presets" role="group" :aria-label="i18n.t('pdf_corpus.units_presets')">
        <button
          v-for="preset in CHAR_PRESETS"
          :key="preset"
          type="button"
          class="preset"
          :class="{ 'is-selected': Number(chars) === preset }"
          :disabled="disabled"
          @click="chars = preset"
        >
          {{ preset }}
        </button>
      </div>
      <small v-if="!charsValid" role="alert">{{ i18n.t("pdf_corpus.units_chars_invalid") }}</small>
    </div>

    <div class="unit-preview" :aria-busy="loading" aria-live="polite">
      <template v-if="error">
        <p class="unit-error" role="alert">{{ error }}</p>
      </template>
      <template v-else-if="preview">
        <dl class="unit-stats">
          <div>
            <dt>{{ i18n.t("pdf_corpus.units_count") }}</dt>
            <dd>{{ preview.unit_count.toLocaleString() }}</dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.units_median") }}</dt>
            <dd>{{ preview.median_chars.toLocaleString() }}</dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.units_range") }}</dt>
            <dd>
              {{ preview.min_chars.toLocaleString() }}–{{ preview.max_chars.toLocaleString() }}
            </dd>
          </div>
        </dl>
        <ol class="unit-sample" :aria-label="i18n.t('pdf_corpus.units_sample')">
          <li v-for="unit in preview.sample" :key="unit.block_id">
            <code>{{ unit.block_id }}</code>
            <span>{{ unit.text }}</span>
          </li>
        </ol>
      </template>
      <p v-else class="unit-loading">{{ i18n.t("pdf_corpus.units_loading") }}</p>
    </div>

    <footer class="unit-actions">
      <p>{{ i18n.t("pdf_corpus.units_apply_help") }}</p>
      <button
        type="button"
        class="btn primary"
        :disabled="disabled || busy || unchanged || (mode === 'chars' && !charsValid)"
        @click="apply"
      >
        {{ i18n.t("pdf_corpus.units_apply") }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
.unit-policy {
  display: grid;
  gap: var(--space-4, 16px);
  padding: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}
.unit-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}
.unit-head h4 {
  margin: 0;
  font-family: var(--font-reading);
  font-size: var(--fs-lg);
  font-weight: var(--fw-semibold);
}
.unit-head p {
  max-inline-size: 70ch;
  margin: 4px 0 0;
  color: var(--text-tertiary);
  font-size: var(--fs-base);
  line-height: var(--lh-normal);
}
.unit-pending {
  flex: none;
  padding: 2px 10px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-pill);
  color: var(--tone-warn-fg);
  background: var(--tone-warn-bg);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
}
.unit-modes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: var(--space-2, 8px);
  min-inline-size: 0;
  margin: 0;
  padding: 0;
  border: 0;
}
.unit-mode {
  position: relative;
  font-weight: var(--fw-regular);
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}
.unit-mode:hover {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
  transform: translateY(-1px);
}
.unit-mode.is-selected {
  border-color: var(--ui-accent, var(--accent));
  background: var(--surface-selected);
  box-shadow: 0 0 0 1px var(--ui-accent, var(--accent));
}
.unit-mode input {
  position: absolute;
  inset-block-start: 10px;
  inset-inline-end: 10px;
  inline-size: 18px;
  block-size: 18px;
  margin: 0;
  accent-color: var(--ui-accent, var(--accent));
}
.unit-mode input:focus-visible {
  outline: none;
}
.unit-mode:has(input:focus-visible) {
  outline: var(--focus-ring-width) solid var(--ui-accent, var(--accent));
  outline-offset: var(--focus-ring-offset);
}
.unit-glyph {
  inline-size: 64px;
  block-size: 40px;
  fill: color-mix(in srgb, var(--ui-accent, var(--accent)) 55%, var(--surface-inset));
}
.unit-mode.is-selected .unit-glyph {
  fill: var(--ui-accent, var(--accent));
}
.unit-copy {
  display: grid;
  gap: 2px;
}
.unit-copy strong {
  font-size: var(--fs-base);
  line-height: var(--lh-tight);
}
.unit-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.unit-chars {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: var(--radius-card);
  background: var(--surface-inset);
}
.unit-chars input {
  inline-size: 120px;
}
.unit-chars small {
  flex-basis: 100%;
  color: var(--tone-danger-fg);
}
.unit-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.preset {
  min-block-size: 28px;
  padding: 2px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  background: var(--surface-card);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}
.preset.is-selected {
  border-color: var(--ui-accent, var(--accent));
  color: var(--accent-fg);
  background: var(--surface-selected);
  font-weight: var(--fw-bold);
}
.unit-preview {
  display: grid;
  gap: var(--space-3, 12px);
  min-block-size: 96px;
}
.unit-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-2, 8px);
  margin: 0;
}
.unit-stats div {
  display: grid;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.unit-stats dt {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.unit-stats dd {
  margin: 0;
  font-size: var(--fs-xl);
  font-weight: var(--fw-bold);
  font-variant-numeric: tabular-nums;
}
.unit-sample {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.unit-sample li {
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 6px 10px;
  border-inline-start: 3px solid var(--ui-accent, var(--accent));
  border-radius: var(--radius-xs);
  background: var(--surface-inset);
  font-family: var(--font-reading);
  font-size: var(--fs-base);
}
.unit-sample code {
  flex: none;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}
.unit-sample span {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}
.unit-loading,
.unit-error {
  margin: 0;
  color: var(--text-tertiary);
}
.unit-error {
  color: var(--tone-danger-fg);
}
.unit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.unit-actions p {
  max-inline-size: 64ch;
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
@media (prefers-reduced-motion: reduce) {
  .unit-mode {
    transition: none;
  }
  .unit-mode:hover {
    transform: none;
  }
}
</style>

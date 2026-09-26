<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiTooltip from "./ui/UiTooltip.vue";
import type { RecordSizingPolicy } from "../types/corpus";
import {
  autoRecordSizingLimits,
  invalidRecordSizingFields,
  limitsAreAutomatic,
  RECORD_SIZING_MIN,
  recordSizingMinimums,
  type ObservedRecordSizes,
} from "../features/corpus-builder/domain/recordSizing";
import CorpusRecordSizingRuler from "./CorpusRecordSizingRuler.vue";

/**
 * Record length: a target, how far from it is fine, and two exception limits. The limits follow the target
 * automatically (always valid); turn that off to set them yourself, with the smallest allowed value shown
 * beside each field and a one-click fix instead of a bare error.
 */
const props = defineProps<{
  modelValue: RecordSizingPolicy;
  disabled?: boolean;
  observed?: ObservedRecordSizes | null;
}>();
const emit = defineEmits<{ (event: "update:modelValue", value: RecordSizingPolicy): void }>();
const i18n = useI18nStore();

const PRESETS = [
  { key: "sentence", preferred: 150, tolerance: 30 },
  { key: "short", preferred: 400, tolerance: 60 },
  { key: "paragraph", preferred: 900, tolerance: 120 },
  { key: "default", preferred: 1750, tolerance: 200 },
] as const;

const custom = ref(!limitsAreAutomatic(props.modelValue));
watch(
  () => props.modelValue,
  (value) => {
    // Values that happen to match the automatic rule are automatic; anything else is the reviewer's own.
    if (limitsAreAutomatic(value)) custom.value = false;
  },
);

const preferred = computed(() => Number(props.modelValue.preferred_record_chars));
const tolerance = computed(() => Number(props.modelValue.record_length_tolerance));
const low = computed(() => Math.max(0, preferred.value - tolerance.value));
const high = computed(() => preferred.value + tolerance.value);
const auto = computed(() => autoRecordSizingLimits(preferred.value, tolerance.value));
const invalid = computed(() => invalidRecordSizingFields(props.modelValue));
const minimums = computed(() => recordSizingMinimums(props.modelValue));

function commit(next: RecordSizingPolicy) {
  emit("update:modelValue", next);
}
function patch(key: keyof RecordSizingPolicy, event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(raw)) return;
  const next = { ...props.modelValue, [key]: Math.round(raw) };
  // Following the target keeps an automatic policy valid; a custom one is never rewritten silently.
  if (!custom.value && (key === "preferred_record_chars" || key === "record_length_tolerance")) {
    Object.assign(
      next,
      autoRecordSizingLimits(next.preferred_record_chars, next.record_length_tolerance),
    );
  }
  commit(next);
}
function setAutomatic(on: boolean) {
  custom.value = !on;
  if (on) commit({ ...props.modelValue, ...auto.value });
}
function usePreset(preset: (typeof PRESETS)[number]) {
  const limits = autoRecordSizingLimits(preset.preferred, preset.tolerance);
  custom.value = false;
  commit({
    preferred_record_chars: preset.preferred,
    record_length_tolerance: preset.tolerance,
    ...limits,
  });
}
function fix(key: "long_record_chars" | "absolute_record_chars") {
  const next = { ...props.modelValue, [key]: minimums.value[key] };
  if (key === "long_record_chars" && next.absolute_record_chars < next.long_record_chars)
    next.absolute_record_chars = next.long_record_chars;
  commit(next);
}

// The ruler: everything on one scale so the relationship between the four numbers is visible.
</script>

<template>
  <fieldset class="record-sizing" :disabled="disabled" aria-describedby="record-sizing-help">
    <legend>
      {{ i18n.t("pdf_corpus.record_sizing.title")
      }}<UiTooltip
        :text="i18n.t('pdf_corpus.record_sizing.characters_help')"
        :label="i18n.t('pdf_corpus.record_sizing.characters_help_label')"
        placement="bottom"
      />
    </legend>
    <p id="record-sizing-help" class="help">{{ i18n.t("pdf_corpus.record_sizing.help") }}</p>

    <CorpusRecordSizingRuler :policy="modelValue" :observed="observed" />

    <div
      class="presets"
      role="group"
      :aria-label="i18n.t('pdf_corpus.record_sizing.presets_title')"
    >
      <span class="presets-title">{{ i18n.t("pdf_corpus.record_sizing.presets_title") }}</span>
      <button
        v-for="preset in PRESETS"
        :key="preset.key"
        type="button"
        class="preset"
        :class="{ 'is-selected': preferred === preset.preferred && tolerance === preset.tolerance }"
        @click="usePreset(preset)"
      >
        {{ i18n.t(`pdf_corpus.record_sizing.preset_${preset.key}`) }}
        <small>{{ preset.preferred.toLocaleString() }}</small>
      </button>
    </div>

    <div class="primary-grid">
      <label for="corpus-preferred-chars"
        ><span>{{ i18n.t("pdf_corpus.record_sizing.preferred") }}</span
        ><input
          id="corpus-preferred-chars"
          class="control"
          type="number"
          :min="RECORD_SIZING_MIN.preferred_record_chars"
          max="12000"
          step="50"
          :value="modelValue.preferred_record_chars"
          @input="patch('preferred_record_chars', $event)"
        /><small
          >{{
            i18n.tf("pdf_corpus.record_sizing.preferred_range", {
              low: low.toLocaleString(),
              high: high.toLocaleString(),
            })
          }}
          ·
          {{
            i18n.tf("pdf_corpus.record_sizing.about_words", {
              count: Math.max(1, Math.round(preferred / 6)).toLocaleString(),
            })
          }}</small
        ></label
      >
      <label for="corpus-tolerance-chars"
        ><span>{{ i18n.t("pdf_corpus.record_sizing.tolerance") }}</span
        ><input
          id="corpus-tolerance-chars"
          class="control"
          type="number"
          :min="RECORD_SIZING_MIN.record_length_tolerance"
          max="2000"
          step="10"
          :value="modelValue.record_length_tolerance"
          @input="patch('record_length_tolerance', $event)"
        /><small>{{ i18n.t("pdf_corpus.record_sizing.tolerance_help") }}</small></label
      >
    </div>

    <label class="auto-switch">
      <input
        type="checkbox"
        :checked="!custom"
        @change="setAutomatic(($event.target as HTMLInputElement).checked)"
      />
      <span>
        <b>{{ i18n.t("pdf_corpus.record_sizing.auto") }}</b>
        <small>{{
          i18n.tf("pdf_corpus.record_sizing.auto_help", {
            long: auto.long_record_chars.toLocaleString(),
            absolute: auto.absolute_record_chars.toLocaleString(),
          })
        }}</small>
      </span>
    </label>

    <div v-if="custom" class="advanced-grid">
      <div class="limit">
        <label for="corpus-long-chars"
          ><span>{{ i18n.t("pdf_corpus.record_sizing.long") }}</span
          ><input
            id="corpus-long-chars"
            class="control"
            type="number"
            :min="minimums.long_record_chars"
            max="24000"
            step="50"
            :value="modelValue.long_record_chars"
            :aria-invalid="invalid.includes('long_record_chars')"
            aria-describedby="long-hint"
            @input="patch('long_record_chars', $event)"
          /><small>{{ i18n.t("pdf_corpus.record_sizing.long_help") }}</small></label
        >
        <p
          id="long-hint"
          class="hint"
          :class="{ bad: invalid.includes('long_record_chars') }"
          :role="invalid.includes('long_record_chars') ? 'alert' : undefined"
        >
          {{
            i18n.tf("pdf_corpus.record_sizing.min_hint", {
              min: minimums.long_record_chars.toLocaleString(),
            })
          }}
          <button
            v-if="invalid.includes('long_record_chars')"
            type="button"
            class="fix"
            @click="fix('long_record_chars')"
          >
            {{
              i18n.tf("pdf_corpus.record_sizing.fix", {
                min: minimums.long_record_chars.toLocaleString(),
              })
            }}
          </button>
        </p>
      </div>
      <div class="limit">
        <label for="corpus-absolute-chars"
          ><span>{{ i18n.t("pdf_corpus.record_sizing.absolute") }}</span
          ><input
            id="corpus-absolute-chars"
            class="control"
            type="number"
            :min="minimums.absolute_record_chars"
            max="48000"
            step="100"
            :value="modelValue.absolute_record_chars"
            :aria-invalid="invalid.includes('absolute_record_chars')"
            aria-describedby="absolute-hint"
            @input="patch('absolute_record_chars', $event)"
          /><small>{{ i18n.t("pdf_corpus.record_sizing.absolute_help") }}</small></label
        >
        <p
          id="absolute-hint"
          class="hint"
          :class="{ bad: invalid.includes('absolute_record_chars') }"
          :role="invalid.includes('absolute_record_chars') ? 'alert' : undefined"
        >
          {{
            i18n.tf("pdf_corpus.record_sizing.min_hint", {
              min: minimums.absolute_record_chars.toLocaleString(),
            })
          }}
          <button
            v-if="invalid.includes('absolute_record_chars')"
            type="button"
            class="fix"
            @click="fix('absolute_record_chars')"
          >
            {{
              i18n.tf("pdf_corpus.record_sizing.fix", {
                min: minimums.absolute_record_chars.toLocaleString(),
              })
            }}
          </button>
        </p>
      </div>
    </div>
    <p v-if="invalid.length" class="sizing-warning" role="status">
      {{ i18n.t("pdf_corpus.record_sizing.invalid") }}
    </p>
  </fieldset>
</template>

<style scoped>
.record-sizing {
  display: grid;
  gap: 12px;
  min-inline-size: 0;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.record-sizing legend {
  padding-inline: 4px;
  font-size: 0.8125rem;
  font-weight: 800;
}
.help {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.presets-title {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 700;
}
.preset {
  min-block-size: 28px;
  padding: 2px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  color: var(--text);
  background: var(--card);
  font-size: 0.8125rem;
  cursor: pointer;
}
.preset small {
  margin-inline-start: 4px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.preset:hover {
  border-color: var(--accent);
}
.preset.is-selected {
  border-color: var(--accent);
  background: var(--surface-selected);
  font-weight: 800;
}
.primary-grid,
.advanced-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.record-sizing label {
  display: grid;
  gap: 4px;
  font-size: 0.8125rem;
  font-weight: 700;
}
.record-sizing small {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.35;
}
.auto-switch {
  display: flex !important;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-inset);
  cursor: pointer;
}
.auto-switch input {
  inline-size: 18px;
  block-size: 18px;
  margin: 2px 0 0;
  accent-color: var(--accent);
}
.auto-switch span {
  display: grid;
  gap: 2px;
}
.limit {
  display: grid;
  gap: 4px;
  align-content: start;
}
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.hint.bad {
  color: var(--tone-danger-fg);
  font-weight: 700;
}
.fix {
  margin-inline-start: 6px;
  padding: 1px 10px;
  border: 1px solid var(--tone-danger-edge);
  border-radius: var(--radius-pill);
  color: var(--tone-danger-fg);
  background: var(--tone-danger-bg);
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}
.sizing-warning {
  margin: 0;
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.record-sizing :is(button, input):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 720px) {
  .primary-grid,
  .advanced-grid {
    grid-template-columns: 1fr;
  }
}
</style>

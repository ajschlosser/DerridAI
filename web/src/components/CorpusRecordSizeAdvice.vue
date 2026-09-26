<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  corpusBuilderApi,
  type PdfAsset,
  type SourceUnitPolicy,
  type SourceUnitPreview,
} from "../api/corpus";
import type { RecordSizingPolicy } from "../types/corpus";
import { useI18nStore } from "../stores/i18n";

/**
 * Records are built from whole source units, so they can never be smaller than the units. When the
 * record length you ask for is shorter than the source's typical unit, say so and offer the fix.
 */
const props = defineProps<{ asset: PdfAsset; sizing: RecordSizingPolicy; disabled?: boolean }>();
const emit = defineEmits<{ apply: [policy: SourceUnitPolicy] }>();
const i18n = useI18nStore();

const stats = ref<SourceUnitPreview | null>(null);
let ticket = 0;

async function load() {
  const mine = ++ticket;
  stats.value = null;
  try {
    // "default" on this asset describes its units exactly as they are now.
    const result = await corpusBuilderApi.previewUnitPolicy(props.asset.asset_id, {
      mode: "default",
    });
    if (mine === ticket) stats.value = result;
  } catch {
    // Advice is a convenience; the build settings are unaffected.
    if (mine === ticket) stats.value = null;
  }
}
watch(() => props.asset.asset_id, load, { immediate: true });

const band = computed(
  () => Number(props.sizing.preferred_record_chars) + Number(props.sizing.record_length_tolerance),
);
const coarse = computed(() => Boolean(stats.value && stats.value.median_chars > band.value * 1.25));
const current = computed(() => props.asset.unit_policy?.mode ?? "default");
const canSentence = computed(() => current.value !== "sentence");
const canChars = computed(
  () =>
    Number(props.sizing.preferred_record_chars) >= 60 &&
    !(
      current.value === "chars" &&
      props.asset.unit_policy?.chars === props.sizing.preferred_record_chars
    ),
);
</script>

<template>
  <aside v-if="coarse && stats" class="size-advice" role="note" aria-labelledby="size-advice-title">
    <div class="advice-copy">
      <h4 id="size-advice-title">{{ i18n.t("pdf_corpus.size_advice_title") }}</h4>
      <p>
        {{
          i18n.tf("pdf_corpus.size_advice_body", {
            target: Number(sizing.preferred_record_chars).toLocaleString(),
            median: stats.median_chars.toLocaleString(),
            longest: stats.max_chars.toLocaleString(),
          })
        }}
      </p>
    </div>
    <div class="advice-actions">
      <button
        v-if="canSentence"
        type="button"
        class="btn primary"
        :disabled="disabled"
        @click="emit('apply', { mode: 'sentence' })"
      >
        {{ i18n.t("pdf_corpus.size_advice_sentences") }}
      </button>
      <button
        v-if="canChars"
        type="button"
        class="btn"
        :disabled="disabled"
        @click="emit('apply', { mode: 'chars', chars: Number(sizing.preferred_record_chars) })"
      >
        {{
          i18n.tf("pdf_corpus.size_advice_chars", {
            n: Number(sizing.preferred_record_chars).toLocaleString(),
          })
        }}
      </button>
    </div>
  </aside>
</template>

<style scoped>
.size-advice {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid var(--tone-warn-edge);
  border-inline-start: 4px solid var(--tone-warn-border);
  border-radius: var(--radius-card);
  color: var(--tone-warn-fg);
  background: var(--tone-warn-bg);
}
.advice-copy {
  max-inline-size: 70ch;
}
.size-advice h4 {
  margin: 0 0 4px;
  font-size: var(--fs-md);
}
.size-advice p {
  margin: 0;
  font-size: var(--fs-base);
  line-height: var(--lh-normal);
}
.advice-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>

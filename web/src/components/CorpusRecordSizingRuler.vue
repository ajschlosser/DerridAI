<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { RecordSizingPolicy } from "../types/corpus";
import type { ObservedRecordSizes } from "../features/corpus-builder/domain/recordSizing";

/**
 * One scale for the record-length policy (short / target / allowed if needed / ceiling) and, when there is a
 * previous build, the sizes it actually produced, so the policy can be judged against reality.
 */
const props = defineProps<{ policy: RecordSizingPolicy; observed?: ObservedRecordSizes | null }>();
const i18n = useI18nStore();

const low = computed(() =>
  Math.max(
    0,
    Number(props.policy.preferred_record_chars) - Number(props.policy.record_length_tolerance),
  ),
);
const high = computed(
  () => Number(props.policy.preferred_record_chars) + Number(props.policy.record_length_tolerance),
);

const observed = computed(() => {
  const o = props.observed;
  const median = Number(o?.median_record_chars || 0);
  if (!o || !(median > 0)) return null;
  const p10 = Number(o.p10_record_chars || 0);
  const p90 = Math.max(Number(o.p90_record_chars || 0), median);
  return {
    p10: Math.min(p10 || median, median),
    median,
    p90,
    max: Number(o.max_record_chars || p90),
  };
});
// The scale reaches the ceiling and the bulk of what was built, but not a single runaway record: the ruler stays
// readable, and the maximum is reported in words instead.
const scaleMax = computed(() =>
  Math.max(Number(props.policy.absolute_record_chars), (observed.value?.p90 ?? 0) * 1.1, 400),
);
const pct = (value: number) => `${Math.min(100, Math.max(0, (value / scaleMax.value) * 100))}%`;
const segments = computed(() => {
  const long = Number(props.policy.long_record_chars);
  const absolute = Number(props.policy.absolute_record_chars);
  return {
    short: { left: "0%", width: pct(low.value) },
    target: { left: pct(low.value), width: `calc(${pct(high.value)} - ${pct(low.value)})` },
    exception: {
      left: pct(high.value),
      width: `calc(${pct(Math.max(high.value, long))} - ${pct(high.value)})`,
    },
    ceiling: {
      left: pct(Math.max(high.value, long)),
      width: `calc(${pct(Math.max(long, absolute))} - ${pct(Math.max(high.value, long))})`,
    },
    absolute: pct(absolute),
  };
});
const observedSpan = computed(() => {
  const o = observed.value;
  if (!o) return null;
  return {
    left: pct(o.p10),
    width: `calc(${pct(o.p90)} - ${pct(o.p10)})`,
    median: pct(o.median),
  };
});
const observedLabel = computed(() =>
  observed.value
    ? i18n.tf("pdf_corpus.record_sizing.ruler_observed", {
        median: observed.value.median.toLocaleString(),
        p10: observed.value.p10.toLocaleString(),
        p90: observed.value.p90.toLocaleString(),
        max: observed.value.max.toLocaleString(),
      })
    : "",
);
const rulerLabel = computed(() =>
  i18n.tf("pdf_corpus.record_sizing.ruler_label", {
    low: low.value.toLocaleString(),
    high: high.value.toLocaleString(),
    long: Number(props.policy.long_record_chars).toLocaleString(),
    absolute: Number(props.policy.absolute_record_chars).toLocaleString(),
  }),
);
</script>

<template>
  <div class="ruler" role="img" :aria-label="rulerLabel">
    <div class="track">
      <span class="seg short" :style="segments.short"></span>
      <span class="seg target" :style="segments.target"></span>
      <span class="seg exception" :style="segments.exception"></span>
      <span class="seg ceiling" :style="segments.ceiling"></span>
    </div>
    <div v-if="observedSpan" class="observed" aria-hidden="true">
      <span
        class="observed-band"
        :style="{ left: observedSpan.left, width: observedSpan.width }"
      ></span>
      <span class="observed-median" :style="{ left: observedSpan.median }"></span>
    </div>
    <p v-if="observedLabel" class="observed-note">{{ observedLabel }}</p>
    <ul class="legend" aria-hidden="true">
      <li class="k-short">
        <b>&lt; {{ low.toLocaleString() }}</b>
        {{ i18n.t("pdf_corpus.record_sizing.ruler_short") }}
      </li>
      <li class="k-target">
        <b>{{ low.toLocaleString() }}–{{ high.toLocaleString() }}</b>
        {{ i18n.t("pdf_corpus.record_sizing.ruler_target") }}
      </li>
      <li class="k-exception">
        <b>≤ {{ Number(policy.long_record_chars).toLocaleString() }}</b>
        {{ i18n.t("pdf_corpus.record_sizing.ruler_exception") }}
      </li>
      <li class="k-ceiling">
        <b>≤ {{ Number(policy.absolute_record_chars).toLocaleString() }}</b>
        {{ i18n.t("pdf_corpus.record_sizing.ruler_ceiling") }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ruler {
  display: grid;
  gap: 8px;
}
.track {
  position: relative;
  block-size: 14px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  overflow: hidden;
}
.seg {
  position: absolute;
  inset-block: 0;
  transition:
    left var(--motion-base) var(--ease-standard),
    width var(--motion-base) var(--ease-standard);
}
.seg.short {
  background: var(--border-strong, var(--line));
  opacity: 0.5;
}
.seg.target {
  background: var(--tone-ok-border);
}
.seg.exception {
  background: var(--tone-warn-border);
  opacity: 0.75;
}
.seg.ceiling {
  background: var(--tone-danger-border);
  opacity: 0.6;
}
.observed {
  position: relative;
  block-size: 10px;
  margin-block-start: -2px;
}
.observed-band {
  position: absolute;
  inset-block: 3px;
  border-radius: var(--radius-pill);
  background: var(--accent);
  opacity: 0.55;
}
.observed-median {
  position: absolute;
  inset-block: 0;
  inline-size: 3px;
  margin-inline-start: -1px;
  border-radius: 2px;
  background: var(--accent);
}
.observed-note {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--muted);
  font-size: 0.8125rem;
}
.legend li::before {
  content: "";
  display: inline-block;
  inline-size: 10px;
  block-size: 10px;
  margin-inline-end: 6px;
  border-radius: 3px;
}
.legend .k-short::before {
  background: var(--border-strong, var(--line));
}
.legend .k-target::before {
  background: var(--tone-ok-border);
}
.legend .k-exception::before {
  background: var(--tone-warn-border);
}
.legend .k-ceiling::before {
  background: var(--tone-danger-border);
}
.legend b {
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
@media (prefers-reduced-motion: reduce) {
  .seg {
    transition: none;
  }
}
</style>

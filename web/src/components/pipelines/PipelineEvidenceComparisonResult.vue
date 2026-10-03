<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import UiButton from "../ui/UiButton.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  EvidencePipelineComparisonResult,
  EvidencePipelineComparisonSide,
} from "../../types/pipelines";

const props = defineProps<{
  result: EvidencePipelineComparisonResult;
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

function percent(value: number) {
  return new Intl.NumberFormat(i18n.locale, { style: "percent", maximumFractionDigits: 0 }).format(
    value,
  );
}
function seconds(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value.toFixed(value < 10 ? 2 : 1)} s`;
}
function sideTitle(side: EvidencePipelineComparisonSide) {
  return `${side.pipeline.pipeline_id || "—"} · v${side.pipeline.pipeline_version ?? "—"}`;
}
function sidePipelineKey(side: EvidencePipelineComparisonSide) {
  const id = side.pipeline.pipeline_id;
  const version = side.pipeline.pipeline_version;
  return id && version != null ? `${id}@${version}` : "";
}

const rows = computed(() => {
  const leftRank = new Map(props.result.left.candidates.map((item) => [item.block_id, item.rank]));
  const rightRank = new Map(
    props.result.right.candidates.map((item) => [item.block_id, item.rank]),
  );
  const ordered = [
    ...props.result.comparison.shared_block_ids,
    ...props.result.comparison.left_only_block_ids,
    ...props.result.comparison.right_only_block_ids,
  ];
  return ordered.map((blockId) => {
    const left = leftRank.get(blockId);
    const right = rightRank.get(blockId);
    return {
      blockId,
      left: left != null ? `#${left}` : "—",
      right: right != null ? `#${right}` : "—",
      presence: left != null && right != null ? "both" : left != null ? "left" : "right",
    };
  });
});
</script>

<template>
  <section class="comparison-result" aria-labelledby="evidence-comparison-result-title">
    <h3 id="evidence-comparison-result-title" class="sr-only">
      {{ t("pipelines.compare_aligned_blocks", "Suggested blocks, aligned by block ID") }}
    </h3>
    <dl class="comparison-overview">
      <div>
        <dt class="metric-label">
          {{ t("pipelines.compare_block_overlap", "Suggested-block overlap") }}
          <UiTooltip
            :label="t('pipelines.compare_block_overlap', 'Suggested-block overlap')"
            :text="
              t(
                'pipelines.compare_block_overlap_help',
                'Jaccard overlap compares the source-block IDs each version selected. It measures similarity between outputs, not scholarly quality.',
              )
            "
          />
        </dt>
        <dd>
          <strong>{{ percent(result.comparison.jaccard_overlap) }}</strong>
          <small>
            {{ result.comparison.shared_count }} / {{ result.comparison.union_count }}
            {{ t("pipelines.compare_shared_union_blocks", "shared / distinct blocks") }}
          </small>
        </dd>
      </div>
      <div>
        <dt>{{ t("pipelines.compare_left_time", "Pipeline A time") }}</dt>
        <dd>{{ seconds(result.left.elapsed_seconds) }}</dd>
      </div>
      <div>
        <dt>{{ t("pipelines.compare_right_time", "Pipeline B time") }}</dt>
        <dd>{{ seconds(result.right.elapsed_seconds) }}</dd>
      </div>
    </dl>

    <div class="side-meta">
      <article
        v-for="(side, index) in [result.left, result.right]"
        :key="sidePipelineKey(side) || String(index)"
      >
        <h4>{{ sideTitle(side) }}</h4>
        <p v-if="side.winning_strategy">
          {{ t("pipelines.compare_winning_strategy", "Winning strategy") }}:
          {{ side.winning_strategy }}
        </p>
        <p v-if="side.pipeline.celf_compliant != null">
          {{ t("pipelines.compare_celf", "cELF compliance") }}:
          {{ side.pipeline.celf_compliant ? t("common.yes", "Yes") : t("common.no", "No") }}
        </p>
        <UiButton
          v-if="sidePipelineKey(side)"
          variant="ghost"
          :label="
            t(
              'pipelines.compare_open_configuration_named',
              'Open configuration for {name}',
            ).replace('{name}', sideTitle(side))
          "
          @click="emit('openPipeline', sidePipelineKey(side))"
        />
      </article>
    </div>

    <p v-if="!rows.length" class="note">
      {{ t("pipelines.compare_no_blocks", "Neither pipeline selected source blocks.") }}
    </p>
    <table v-else class="aligned">
      <caption>
        {{
          t("pipelines.compare_aligned_blocks", "Suggested blocks, aligned by block ID")
        }}
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ t("pipelines.compare_block", "Block") }}</th>
          <th scope="col">{{ t("pipelines.compare_left", "Pipeline A") }}</th>
          <th scope="col">{{ t("pipelines.compare_right", "Pipeline B") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.blockId" :data-presence="row.presence">
          <th scope="row">
            <code>{{ row.blockId }}</code>
            <small v-if="row.presence === 'left'" class="presence">
              {{ t("pipelines.compare_only_left", "Only in Pipeline A") }}
            </small>
            <small v-else-if="row.presence === 'right'" class="presence">
              {{ t("pipelines.compare_only_right", "Only in Pipeline B") }}
            </small>
          </th>
          <td>{{ row.left }}</td>
          <td>{{ row.right }}</td>
        </tr>
      </tbody>
    </table>
    <p class="note">
      {{
        t(
          "pipelines.compare_overlap_interpretation",
          "Overlap describes how similar the selected evidence sets are; it does not measure scholarly quality.",
        )
      }}
    </p>
  </section>
</template>

<style scoped>
.comparison-result {
  display: grid;
  gap: var(--space-4);
}
.comparison-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}
.comparison-overview dt,
.metric-label {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.comparison-overview dd {
  margin: var(--space-1) 0 0;
}
.comparison-overview strong {
  display: block;
  font-size: 1.25rem;
}
.comparison-overview small {
  color: var(--text-secondary);
}
.side-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}
.side-meta h4 {
  margin: 0 0 var(--space-1);
  font-size: 0.9375rem;
}
.side-meta p {
  margin: 0 0 var(--space-1);
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.aligned {
  width: 100%;
  border-collapse: collapse;
}
.aligned th,
.aligned td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
  text-align: left;
  font-size: 0.875rem;
}
.aligned caption {
  caption-side: top;
  text-align: left;
  margin-bottom: var(--space-2);
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.presence {
  display: block;
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.note {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
@media (max-width: 860px) {
  .comparison-overview,
  .side-meta {
    grid-template-columns: 1fr;
  }
}
</style>

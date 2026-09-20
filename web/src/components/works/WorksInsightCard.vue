<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { WorksInsight } from "../../types/works";

const props = defineProps<{insight: WorksInsight}>();
const emit = defineEmits<{search: [field: string, value: string]}>();
const i18n = useI18nStore();
const colors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)"];

const total = computed(() => props.insight.values.reduce((sum, item) => sum + Number(item.value || 0), 0));
const pieStyle = computed(() => {
  if (!total.value) return {};
  let cursor = 0;
  const stops = props.insight.values.map((item, index) => {
    const start = cursor;
    cursor += Number(item.value || 0) / total.value * 100;
    return `${colors[index % colors.length]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
  });
  return {background: `conic-gradient(${stops.join(",")})`};
});

function percent(value: number) {
  const pct = total.value ? Number(value || 0) / total.value * 100 : 0;
  return `${pct.toFixed(pct >= 10 ? 0 : 1)}%`;
}
</script>
<template>
  <article class="work-insight-card" :class="{'work-insight-card-pie': props.insight.type === 'pie'}">
    <h3>{{ props.insight.heading }}</h3>
    <template v-if="props.insight.type === 'pie'">
      <p v-if="!total" class="note">{{ i18n.t("works.no_indexed_values", "No indexed values in the loaded records.") }}</p>
      <div v-else class="work-insight-pie-layout">
        <div class="work-insight-pie" :style="pieStyle" role="img" :aria-label="props.insight.title"></div>
        <ol class="work-insight-pie-legend">
          <li v-for="(item, index) in props.insight.values" :key="item.key">
            <span v-if="item.other" class="work-insight-pie-label" :aria-label="item.key">
              <i :style="{background: colors[index % colors.length]}"></i>
              <span>{{ item.key }}</span>
            </span>
            <button v-else type="button" :data-work-insight-field="props.insight.field" :data-work-insight-value="item.key" @click="emit('search', props.insight.field, item.key)">
              <i :style="{background: colors[index % colors.length]}"></i>
              <span>{{ item.key }}</span>
            </button>
            <b>{{ percent(item.value) }}</b>
          </li>
        </ol>
      </div>
    </template>
    <ol v-else>
      <li v-if="!props.insight.values.length" class="note">{{ i18n.t("works.no_indexed_values", "No indexed values in the loaded records.") }}</li>
      <li v-for="item in props.insight.values" :key="item.key">
        <button type="button" :data-work-insight-field="props.insight.field" :data-work-insight-value="item.key" @click="emit('search', props.insight.field, item.key)">
          <span>{{ item.key }}</span>
          <b>{{ Number(item.value).toLocaleString(i18n.locale) }}</b>
        </button>
      </li>
    </ol>
  </article>
</template>

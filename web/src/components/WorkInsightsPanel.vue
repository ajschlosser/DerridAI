<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";

type InsightItem = { label: string; count: number };
type InsightMetric = { id: string; field: string; title: string; items: InsightItem[] };

const props = withDefaults(defineProps<{
  work: string;
  metrics: InsightMetric[];
  description?: string;
}>(), { description: "" });

const emit = defineEmits<{ select: [field: string, value: string] }>();
const i18n = useI18nStore();
</script>

<template>
  <section class="work-insights" :aria-label="i18n.t('works.work_insights', 'Work insights')">
    <header class="work-insights__head">
      <div>
        <span>{{ i18n.t('works.work_insights', 'Work insights') }}</span>
        <h2>{{ i18n.t('works.indexed_patterns', 'Indexed patterns in this work') }}</h2>
      </div>
      <p>{{ props.description || i18n.t('works.work_insights_help', 'Counts are derived from the currently loaded records and use the corpus metadata fields directly.') }}</p>
    </header>
    <div class="work-insights__grid">
      <article v-for="metric in props.metrics" :key="metric.id" class="work-insights__card">
        <h3>{{ metric.title }}</h3>
        <ol v-if="metric.items.length">
          <li v-for="item in metric.items" :key="item.label">
            <button type="button" @click="emit('select', metric.field, item.label)">
              <span :title="item.label">{{ item.label }}</span>
              <b>{{ item.count.toLocaleString(i18n.locale) }}</b>
            </button>
          </li>
        </ol>
        <p v-else>{{ i18n.t('works.no_indexed_values', 'No indexed values in the loaded records.') }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.work-insights{padding:14px;border:1px solid #dde5eb;border-radius:12px;background:linear-gradient(180deg,#fbfcfd,#f7faf8);color:#2b3d55}.work-insights__head{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,.7fr);gap:18px;align-items:end;margin-bottom:11px}.work-insights__head span{font-size:10.5px;font-weight:800;letter-spacing:.055em;text-transform:uppercase;color:#6b7a8e}.work-insights__head h2{margin:2px 0 0;font-size:16px;line-height:1.2}.work-insights__head p{margin:0;color:#6b7a8e;font-size:11.5px;line-height:1.45}.work-insights__grid{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:8px;overflow-x:auto}.work-insights__card{min-width:150px;padding:10px;border:1px solid #e2e8ee;border-radius:9px;background:#fff}.work-insights__card h3{min-height:31px;margin:0 0 7px;color:#4c5e74;font-size:11px;line-height:1.3;text-transform:uppercase;letter-spacing:.035em}.work-insights__card ol{display:grid;gap:4px;margin:0;padding:0;list-style:none}.work-insights__card button{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;width:100%;padding:5px 6px;border:0;border-radius:6px;background:transparent;color:#35485f;text-align:left;cursor:pointer}.work-insights__card button:hover{background:#eef6f1}.work-insights__card button:focus-visible{outline:3px solid #86b89f;outline-offset:1px}.work-insights__card button span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11.5px}.work-insights__card button b{font-size:11px;font-variant-numeric:tabular-nums}.work-insights__card p{margin:0;color:#718096;font-size:11.5px;line-height:1.4}@media(max-width:760px){.work-insights__head{grid-template-columns:1fr}.work-insights__grid{grid-template-columns:repeat(5,minmax(180px,1fr))}}
</style>

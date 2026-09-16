<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../stores/i18n";

type MetricItem = { label: string; value: number; formatted?: string };
type MetricSlide = { id: string; title: string; items: MetricItem[] };
const props = defineProps<{ slides: MetricSlide[] }>();
const emit = defineEmits<{ selectWork: [label: string] }>();
const i18n=useI18nStore();
const index = ref(0);
const active = computed(() => props.slides[index.value] || { id: "empty", title: "", items: [] });
const max = computed(() => Math.max(1, ...active.value.items.map(item => Number(item.value) || 0)));
function move(delta: number) { if (!props.slides.length) return; index.value = (index.value + delta + props.slides.length) % props.slides.length; }
</script>
<template>
  <section class="storybook-metric-carousel" aria-roledescription="carousel" :aria-label="active.title">
    <header><h3>{{ active.title }}</h3><div><button type="button" :aria-label="i18n.t('dashboard.previous_chart','Previous chart')" @click="move(-1)">←</button><span>{{ index + 1 }} / {{ props.slides.length }}</span><button type="button" :aria-label="i18n.t('dashboard.next_chart','Next chart')" @click="move(1)">→</button></div></header>
    <div class="storybook-metric-list">
      <button v-for="item in active.items" :key="item.label" type="button" @click="emit('selectWork', item.label)"><span>{{ item.label }}</span><i><em :style="{ width: `${Math.max(4, Math.round((item.value / max) * 100))}%` }" /></i><b>{{ item.formatted || item.value.toLocaleString(i18n.locale) }}</b></button>
    </div>
    <footer role="tablist" :aria-label="i18n.t('dashboard.work_charts','Work charts')"><button v-for="(slide, slideIndex) in props.slides" :key="slide.id" type="button" role="tab" :class="{ active: slideIndex === index }" :aria-label="slide.title" :aria-selected="slideIndex === index" :tabindex="slideIndex === index ? 0 : -1" @click="index = slideIndex" /></footer>
  </section>
</template>

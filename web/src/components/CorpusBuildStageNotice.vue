<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
defineProps<{stage?:string}>();
const i18n=useI18nStore();
</script>
<template>
  <section class="build-stage-active" role="status" aria-live="polite">
    <span class="eyebrow">{{i18n.t('pdf_corpus.building_records')}}</span>
    <h3>{{i18n.t('pdf_corpus.building_records_title')}}</h3>
    <p>{{i18n.t('pdf_corpus.building_records_help')}}</p>
    <small v-if="stage">{{i18n.t('pdf_corpus.current_stage')}}: {{stage}}</small>
  </section>
</template>
<style scoped>
.build-stage-active{display:grid;gap:5px;padding:18px;border:1px solid var(--line);border-radius:12px;background:var(--soft)}
.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.build-stage-active h3{margin:0;font-size:0.9375rem}.build-stage-active p{margin:0;max-width:72ch;font-size:0.8125rem;line-height:1.5;color:var(--muted)}.build-stage-active small{font-size:.8125rem;color:var(--muted)}
</style>

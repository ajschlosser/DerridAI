<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
defineProps<{stage?:string}>();
const i18n=useI18nStore();
</script>
<template>
  <section class="build-stage-active" role="status" aria-live="polite">
    <span class="eyebrow">{{i18n.t('pdf_corpus.building_records','Building records')}}</span>
    <h3>{{i18n.t('pdf_corpus.building_records_title','Corpus construction is in progress')}}</h3>
    <p>{{i18n.t('pdf_corpus.building_records_help','DerridAI is analyzing document structure and semantic boundaries. The review workspace will appear automatically when reviewable records are persisted.')}}</p>
    <small v-if="stage">{{i18n.t('pdf_corpus.current_stage','Current stage')}}: {{stage}}</small>
  </section>
</template>
<style scoped>
.build-stage-active{display:grid;gap:5px;padding:18px;border:1px solid var(--line);border-radius:12px;background:var(--soft)}
.eyebrow{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.build-stage-active h3{margin:0;font-size:15px}.build-stage-active p{margin:0;max-width:72ch;font-size:10px;line-height:1.5;color:var(--muted)}.build-stage-active small{font-size:9px;color:var(--muted)}
</style>

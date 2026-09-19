<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
const props=defineProps<{build:CorpusBuild}>();
const i18n=useI18nStore();
const events=computed(()=>[...(props.build.build_events||[])].reverse());
function when(value?:string){if(!value)return "—";try{return new Intl.DateTimeFormat(i18n.locale||undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value))}catch{return value}}
</script>
<template>
  <details v-if="events.length" class="timeline">
    <summary>{{i18n.t('pdf_corpus.build_timeline','Build timeline')}} <span>{{events.length}}</span></summary>
    <ol><li v-for="(event,index) in events" :key="`${event.at}-${index}`"><span class="dot" aria-hidden="true"></span><div><b>{{i18n.t(`pdf_corpus.stage.${event.stage}`,String(event.stage||event.status||'').replace(/_/g,' '))}}</b><small>{{when(event.at)}} · {{Math.round(Number(event.progress||0)*100)}}%</small></div></li></ol>
  </details>
</template>
<style scoped>
.timeline{border:1px solid var(--line);border-radius:10px;background:var(--card);overflow:hidden}.timeline>summary{padding:9px 11px;cursor:pointer;font-size:.8125rem;font-weight:800}.timeline>summary span{margin-inline-start:5px;color:var(--muted);font-weight:500}ol{list-style:none;margin:0;padding:6px 12px 12px;display:grid;gap:0;border-top:1px solid var(--line)}li{position:relative;display:grid;grid-template-columns:14px 1fr;gap:8px;padding:8px 0}li:not(:last-child)::after{content:"";position:absolute;inset-inline-start:6px;top:19px;bottom:-8px;border-inline-start:1px solid var(--line)}.dot{width:8px;height:8px;border-radius:50%;background:var(--accent);margin-top:3px;z-index:1}li div{display:grid;gap:2px}b{font-size:.8125rem}small{font-size:.8125rem;color:var(--muted)}
</style>

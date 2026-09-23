<script setup lang="ts">
import { computed } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
const props=defineProps<{record:CorpusRecord}>();
const i18n=useI18nStore();
const items=computed(()=>{
  const rows:Array<{at?:string;kind:string;label:string;detail?:string}>=[];
  for(const entry of props.record.text_revision_history||[]){
    rows.push({at:entry.at,kind:"text",label:entry.source==="automatic_cleanup"?i18n.t("pdf_corpus.history_auto_cleanup"):i18n.t("pdf_corpus.history_text_edit"),detail:entry.diff?i18n.t("pdf_corpus.history_diff_available"):undefined});
  }
  for(const entry of props.record.metadata_decisions||[]){
    const field=String(entry.field||"");
    rows.push({at:entry.at,kind:"metadata",label:i18n.tf("pdf_corpus.history_metadata_change", {field:i18n.t(`record.${field}`,field.replace(/_/g," "))}),detail:entry.source?i18n.t(`pdf_corpus.history_source.${entry.source}`,String(entry.source).replace(/_/g," ")):undefined});
  }
  for(const entry of props.record.metadata_enrichment_history||[]){
    for(const event of entry.informational||[]){
      const field=String(event.field||"");
      const kind=String(event.kind||"agreement");
      const label=kind==="protected_suggestion"
        ? i18n.t("pdf_corpus.history_enrichment_protected")
        : kind==="duplicate"
          ? i18n.t("pdf_corpus.history_enrichment_duplicate")
          : i18n.t("pdf_corpus.history_enrichment_agreement");
      const model=event.model?String(event.model):"";
      const pass=event.pass?i18n.tf("pdf_corpus.enrichment_pass_number", {pass:event.pass}):"";
      rows.push({
        at:event.at||entry.at,
        kind:"enrichment",
        label:field?`${label}: ${i18n.t(`record.${field}`,field.replace(/_/g," "))}`:label,
        detail:[model,pass].filter(Boolean).join(" · ")||undefined,
      });
    }
  }
  for(const entry of props.record.review_events||[]){
    const event=String(entry.event||'review_change');
    rows.push({at:entry.at,kind:'review',label:i18n.t(`pdf_corpus.history_event.${event}`,event.replace(/_/g,' ')),detail:entry.transaction_id?String(entry.transaction_id):undefined});
  }
  return rows.sort((a,b)=>String(b.at||"").localeCompare(String(a.at||""))).slice(0,50);
});
function formatDate(value?:string){if(!value)return "—";try{return new Intl.DateTimeFormat(i18n.locale||undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value))}catch{return value}}
</script>
<template>
<section class="revision-history" aria-labelledby="revision-history-title">
  <header><div><span class="eyebrow">{{i18n.t('pdf_corpus.audit_trail')}}</span><h3 id="revision-history-title">{{i18n.t('pdf_corpus.revision_history')}}</h3></div><span class="count">{{items.length}}</span></header>
  <ol v-if="items.length"><li v-for="(item,index) in items" :key="`${item.at}-${item.kind}-${index}`"><div><b>{{item.label}}</b><small v-if="item.detail">{{item.detail}}</small></div><time :datetime="item.at">{{formatDate(item.at)}}</time></li></ol>
  <p v-else>{{i18n.t('pdf_corpus.no_revision_history')}}</p>
</section>
</template>
<style scoped>
.revision-history{display:grid;gap:10px}.revision-history>header{display:flex;justify-content:space-between;gap:12px;align-items:center}.revision-history h3{margin:2px 0 0;font-size:.9375rem}.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.count{min-width:28px;text-align:center;border:1px solid var(--line);border-radius:999px;padding:3px 7px;font-size:.8125rem}.revision-history ol{list-style:none;margin:0;padding:0;display:grid;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card)}.revision-history li{display:flex;justify-content:space-between;gap:14px;padding:10px 11px;border-bottom:1px solid var(--line)}.revision-history li:last-child{border-bottom:0}.revision-history li>div{display:grid;gap:2px}.revision-history b{font-size:.8125rem}.revision-history small,.revision-history time,.revision-history p{font-size:.8125rem;color:var(--muted);line-height:1.4}.revision-history p{margin:0}.revision-history time{white-space:nowrap}@media(max-width:640px){.revision-history li{display:grid}.revision-history time{white-space:normal}}
</style>
